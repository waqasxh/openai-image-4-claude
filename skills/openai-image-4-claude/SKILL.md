---
name: openai-image-4-claude
description: >
  Generate or edit images using OpenAI's image models (gpt-image). Use this skill when the
  user wants to generate, create, or edit images with OpenAI, ChatGPT images, or gpt-image.
  Keywords: OpenAI image, gpt-image, generate picture, AI art, edit image, icon, illustration.
allowed-tools: Bash, Read, Glob, AskUserQuestion
---

# OpenAI Image Gen Skill

Generate images from text prompts with OpenAI's image API.

## Tiers: economy first, premium only with confirmation

OpenAI's image API has **no free tier**; every call is billed. So the tiers are about cost:

| Tier    | Default model      | Quality | Env override                 |
|---------|--------------------|---------|------------------------------|
| Economy | `gpt-image-1-mini` | low     | `OPENAI_IMAGE_MODEL_ECONOMY` |
| Premium | `gpt-image-1`      | high    | `OPENAI_IMAGE_MODEL_PREMIUM` |

Every run uses **economy by default**. Never pass `--paid` unless the user has explicitly asked
for premium/best quality in this conversation, or confirmed it when you asked
(AskUserQuestion). When they do, add `--paid --confirm-paid`. Approval covers that request only.

If the user is unhappy with economy output, offer premium rather than switching silently.

## First-time setup (once per session)

```bash
"${CLAUDE_PLUGIN_ROOT}/scripts/check_env.sh"
uv sync --project "${CLAUDE_PLUGIN_ROOT}"
```

If the key is missing, tell the user to create `~/.config/openai-image-4-claude/.env` with
`OPENAI_API_KEY=your_key` (key from https://platform.openai.com/api-keys, account needs billing
credit; `gpt-image-1` may also require organization verification).

## Usage

Pass `--cwd "$PWD"` so output lands in the user's project:

```bash
uv run --project "${CLAUDE_PLUGIN_ROOT}" python "${CLAUDE_PLUGIN_ROOT}/main.py" --cwd "$PWD" <output_path> "<prompt>" [options]
```

Format follows the extension (`.png`, `.jpg`, `.webp`).

## Options

| Option           | Short | Description                                                          |
|------------------|-------|----------------------------------------------------------------------|
| `--style`        | `-s`  | Style template (.md with `## Prompt Template` code block, `{subject}`) |
| `--edit`         | `-e`  | Edit an existing image (exactly one prompt)                          |
| `--ref`          | `-r`  | Reference image (repeatable, up to 16); uses the edit endpoint       |
| `--aspect`       | `-a`  | `1:1`, `3:2`, `4:3`, `16:9`, `21:9`, `2:3`, `3:4`, `4:5`, `9:16`     |
| `--paid`         |       | Premium tier; needs `--confirm-paid`                                 |
| `--confirm-paid` |       | Asserts the user confirmed premium usage                             |

Aspect ratios map to the only sizes gpt-image supports: 1024x1024, 1536x1024, 1024x1536.
Ratios like 16:9 are approximated by 3:2; crop afterwards if exact ratio matters.

## Exit codes

| Code | Meaning                                            | What to do                                   |
|------|----------------------------------------------------|----------------------------------------------|
| 0    | Saved                                              | Verify the file and report                   |
| 1    | Generation failed (API error, policy block)        | Show message; adjust prompt and retry        |
| 2    | Invalid input (missing file/key, bad template)     | Fix input or setup                           |
| 3    | Billing, quota, or org verification problem        | Tell the user; do not switch tiers or retry  |

## Examples

`RUN` = `uv run --project "${CLAUDE_PLUGIN_ROOT}" python "${CLAUDE_PLUGIN_ROOT}/main.py" --cwd "$PWD"`

```bash
RUN output.png "A red apple on a wooden table"
RUN images/hero.png "Mountain landscape at dawn" --aspect 16:9
RUN output.png "Change the sky to sunset" --edit input.png
RUN a.png "cube" "sphere"            # -> a_1.png, a_2.png
RUN final.png "Product shot" --paid --confirm-paid   # only after user confirmed
```
