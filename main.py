#!/usr/bin/env python3
"""OpenAI Image Generator.

Generate or edit images with OpenAI's image API (gpt-image models).
Part of the openai-image-4-claude Claude Code plugin.

Setup:
    1. Create an API key at https://platform.openai.com/api-keys (needs billing credit;
       OpenAI's image API has no free tier).
    2. Put OPENAI_API_KEY=... in ~/.config/openai-image-4-claude/.env or export it.
    3. uv sync

Tiers:
    economy (default): gpt-image-1-mini, quality "low"      -> cheapest
    premium (--paid --confirm-paid): gpt-image-1, quality "high"
    Override models with OPENAI_IMAGE_MODEL_ECONOMY / OPENAI_IMAGE_MODEL_PREMIUM.

Exit codes:
    0  all images saved
    1  generation failed (API error, blocked, no image returned)
    2  invalid input (missing file, bad template, missing API key, ...)
    3  billing/quota/org-verification problem; tell the user, do not auto-switch tiers
"""
import argparse
import base64
import io
import os
import re
import sys
from pathlib import Path

import openai
from dotenv import load_dotenv
from openai import OpenAI
from PIL import Image

EXIT_OK = 0
EXIT_FAILED = 1
EXIT_BAD_INPUT = 2
EXIT_BILLING = 3

DEFAULT_ECONOMY_MODEL = "gpt-image-1-mini"
DEFAULT_PREMIUM_MODEL = "gpt-image-1"
QUALITY = {"economy": "low", "premium": "high"}

MAX_REFERENCES = 16

# gpt-image models support these sizes only.
ASPECT_TO_SIZE = {
    "1:1": "1024x1024",
    "3:2": "1536x1024",
    "4:3": "1536x1024",
    "16:9": "1536x1024",
    "21:9": "1536x1024",
    "2:3": "1024x1536",
    "3:4": "1024x1536",
    "4:5": "1024x1536",
    "9:16": "1024x1536",
}


class BillingProblem(Exception):
    """Billing, quota, or organization verification blocks this request."""


class GenerationError(Exception):
    """Generation failed for another reason."""


def load_style_template(style_path: Path) -> str:
    """Load the prompt template code block after a '## Prompt Template' heading."""
    if not style_path.exists():
        raise FileNotFoundError(f"Style file not found: {style_path}")
    content = style_path.read_text(encoding="utf-8")
    pattern = r"(?:##?\s*(?:Prompt\s*)?Template)[^\n]*\n+(?:.*?\n)*?```[^\n]*\n(.*?)```"
    match = re.search(pattern, content, re.IGNORECASE | re.DOTALL)
    if not match:
        raise ValueError(
            f"No prompt template found in {style_path}. "
            "Add a '## Prompt Template' section with a code block."
        )
    return re.sub(
        r"\[YOUR SUBJECT[^\]]*\]|\[SUBJECT\]|\{subject\}",
        "{subject}",
        match.group(1).strip(),
        flags=re.IGNORECASE,
    )


def apply_style_template(template: str, subject: str) -> str:
    """Plain replacement so other braces in the template survive."""
    if "{subject}" in template:
        return template.replace("{subject}", subject)
    return f"{subject}. {template}"


def _is_billing_error(exc: openai.APIStatusError) -> bool:
    """Billing/quota/verification errors that switching prompt or retrying won't fix."""
    text = str(exc).lower()
    code = getattr(exc, "code", None) or ""
    if code in ("insufficient_quota", "billing_hard_limit_reached"):
        return True
    if isinstance(exc, openai.RateLimitError) and "quota" in text:
        return True
    if isinstance(exc, openai.PermissionDeniedError) and "verif" in text:
        return True
    return "billing" in text and exc.status_code in (400, 402, 403, 429)


def _save_image(data: bytes, output_path: Path) -> None:
    formats = {".png": "PNG", ".jpg": "JPEG", ".jpeg": "JPEG", ".webp": "WEBP"}
    fmt = formats.get(output_path.suffix.lower())
    if fmt is None:
        output_path.write_bytes(data)
        return
    with Image.open(io.BytesIO(data)) as img:
        if fmt == "JPEG" and img.mode not in ("RGB", "L"):
            img = img.convert("RGB")
        img.save(output_path, format=fmt)


def _resolve_path(path: Path, base_dir: Path) -> Path:
    return path if path.is_absolute() else base_dir / path


def _open_files(paths: list[Path]) -> list[tuple[str, bytes, str]]:
    """Read images as (name, bytes, mime) tuples the SDK accepts."""
    mimes = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp"}
    return [(p.name, p.read_bytes(), mimes.get(p.suffix.lower(), "image/png")) for p in paths]


def generate(
    prompt: str,
    output_path: Path,
    model: str,
    tier: str,
    size: str,
    input_images: list[Path] | None = None,
) -> None:
    """Request one image and save it. Uses images.edit when input_images are given."""
    client = OpenAI()
    quality = QUALITY[tier]
    try:
        if input_images:
            response = client.images.edit(
                model=model,
                image=_open_files(input_images),
                prompt=prompt,
                size=size,
                quality=quality,
            )
        else:
            response = client.images.generate(
                model=model, prompt=prompt, size=size, quality=quality, n=1
            )
    except openai.APIStatusError as exc:
        if _is_billing_error(exc):
            raise BillingProblem(f"{exc.status_code}: {exc}") from exc
        raise GenerationError(f"API error {exc.status_code}: {exc}") from exc
    except openai.APIConnectionError as exc:
        raise GenerationError(f"Connection error: {exc}") from exc

    item = response.data[0] if response.data else None
    if not item or not getattr(item, "b64_json", None):
        raise GenerationError("No image returned (possibly blocked by content policy).")
    _save_image(base64.b64decode(item.b64_json), output_path)
    print(f"Image saved to: {output_path} (model: {model}, quality: {quality}, size: {size})")


def _load_env(script_dir: Path, base_dir: Path) -> None:
    home_env = Path.home() / ".config" / "openai-image-4-claude" / ".env"
    if home_env.exists():
        load_dotenv(home_env)
    for env_path in (script_dir / ".env", base_dir / ".env"):
        if env_path.exists():
            load_dotenv(env_path, override=False)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate images with OpenAI (economy tier by default)",
        epilog="Exit codes: 0 ok, 1 failed, 2 invalid input, 3 billing/quota problem.",
    )
    parser.add_argument("output", help="Output path for the image")
    parser.add_argument("prompts", nargs="+", help="One or more subjects/prompts")
    parser.add_argument("--style", "-s", help="Path to style template .md file")
    parser.add_argument("--edit", "-e", help="Path to input image to edit")
    parser.add_argument(
        "--ref", "-r", action="append", dest="references",
        help=f"Reference image (repeatable, up to {MAX_REFERENCES} with --edit)",
    )
    parser.add_argument(
        "--aspect", "-a", default="16:9", choices=sorted(ASPECT_TO_SIZE),
        help="Aspect ratio, mapped to the nearest supported size (default: 16:9)",
    )
    parser.add_argument("--paid", action="store_true",
                        help="Premium model (higher cost). Requires --confirm-paid.")
    parser.add_argument("--confirm-paid", action="store_true",
                        help="Assert the user explicitly confirmed premium usage.")
    parser.add_argument("--cwd", help="Base directory for relative paths")
    return parser


def main() -> int:
    args = _build_parser().parse_args()
    base_dir = Path(args.cwd) if args.cwd else Path.cwd()
    script_dir = Path(__file__).parent
    _load_env(script_dir, base_dir)

    if not os.environ.get("OPENAI_API_KEY"):
        print("Error: OPENAI_API_KEY not found in environment")
        print("  1. Create ~/.config/openai-image-4-claude/.env with: OPENAI_API_KEY=your_key")
        print("  2. Or export OPENAI_API_KEY=your_key")
        print("Get a key at: https://platform.openai.com/api-keys")
        return EXIT_BAD_INPUT

    if args.paid and not args.confirm_paid:
        print("Error: --paid requires --confirm-paid, set only after the user explicitly")
        print("confirmed premium usage for this request. Refusing.")
        return EXIT_BAD_INPUT

    tier = "premium" if args.paid else "economy"
    model = (
        os.environ.get("OPENAI_IMAGE_MODEL_PREMIUM") or DEFAULT_PREMIUM_MODEL
        if args.paid
        else os.environ.get("OPENAI_IMAGE_MODEL_ECONOMY") or DEFAULT_ECONOMY_MODEL
    )
    size = ASPECT_TO_SIZE[args.aspect]
    print(f"Tier: {tier} (model: {model})")

    output_path = _resolve_path(Path(args.output), base_dir)

    prompts = args.prompts
    if args.style:
        style_path = _resolve_path(Path(args.style), base_dir)
        if not style_path.exists() and (script_dir / args.style).exists():
            style_path = script_dir / args.style
        try:
            template = load_style_template(style_path)
        except (FileNotFoundError, ValueError) as e:
            print(f"Error: {e}")
            return EXIT_BAD_INPUT
        prompts = [apply_style_template(template, p) for p in prompts]

    input_paths: list[Path] = []
    if args.edit:
        if len(prompts) > 1:
            print("Error: --edit accepts exactly one prompt")
            return EXIT_BAD_INPUT
        input_paths.append(_resolve_path(Path(args.edit), base_dir))
    input_paths.extend(_resolve_path(Path(r), base_dir) for r in args.references or [])
    if input_paths and not args.edit:
        print("Note: --ref images are sent through the edit endpoint as visual references.")
    missing = [p for p in input_paths if not p.exists()]
    if missing:
        for p in missing:
            print(f"Error: Input image not found: {p}")
        return EXIT_BAD_INPUT
    if len(input_paths) > MAX_REFERENCES:
        print(f"Error: at most {MAX_REFERENCES} input images")
        return EXIT_BAD_INPUT

    output_path.parent.mkdir(parents=True, exist_ok=True)
    jobs = (
        [(prompts[0], output_path)]
        if len(prompts) == 1
        else [
            (p, output_path.parent / f"{output_path.stem}_{i}{output_path.suffix}")
            for i, p in enumerate(prompts, 1)
        ]
    )

    failures = 0
    for i, (prompt, path) in enumerate(jobs, 1):
        if len(jobs) > 1:
            print(f"\nGenerating image {i}/{len(jobs)}...")
        try:
            generate(prompt, path, model, tier, size, input_paths or None)
        except BillingProblem as exc:
            print(f"BILLING_PROBLEM: {exc}")
            print("Billing, quota, or organization verification blocks this request.")
            print("Tell the user; do not retry or switch tiers on your own.")
            return EXIT_BILLING
        except GenerationError as exc:
            print(f"Error: {exc}")
            failures += 1

    if failures:
        print(f"\n{failures}/{len(jobs)} image(s) failed.")
        return EXIT_FAILED
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
