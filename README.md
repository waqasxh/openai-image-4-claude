# openai-image-4-claude

A [Claude Code](https://claude.com/claude-code) plugin that generates and edits images with OpenAI's image models (`gpt-image`) from inside Claude Code.

> **Note:** OpenAI's image API has no free tier. Every call is billed, so your OpenAI account needs billing credit. The plugin offers a cheap **economy** tier by default and a **premium** tier that is used only after you confirm.

## Features

- Text-to-image generation
- Edit an existing image (`--edit`) or guide a result with reference images (`--ref`, up to 16)
- Batch generation: several prompts in one run, saved as `name_1.png`, `name_2.png`, ...
- Style templates (markdown files with a `{subject}` placeholder)
- Output formats from the file extension: `.png`, `.jpg`, `.webp`
- Cost guard: premium needs both `--paid` and `--confirm-paid`

## Tiers

| Tier | Default model | Quality | Used when |
|---|---|---|---|
| Economy | `gpt-image-1-mini` | low | Always, by default |
| Premium | `gpt-image-1` | high | Only after you explicitly confirm |

Override the models with `OPENAI_IMAGE_MODEL_ECONOMY` and `OPENAI_IMAGE_MODEL_PREMIUM`. `gpt-image-1` may require [OpenAI organization verification](https://platform.openai.com/settings/organization/general).

## Requirements

- [Claude Code](https://claude.com/claude-code)
- [uv](https://astral.sh/uv) (Python 3.10+)
- An OpenAI API key with billing enabled: <https://platform.openai.com/api-keys>

## Install

```
/plugin marketplace add waqasxh/openai-image-4-claude
/plugin install openai-image-4-claude@openai-image-4-claude
```

Or load it locally for development:

```bash
claude --plugin-dir /path/to/openai-image-4-claude
```

## Configure your API key

Create `~/.config/openai-image-4-claude/.env`:

```
OPENAI_API_KEY=sk-...
```

Alternatively export `OPENAI_API_KEY`, or put a `.env` in the plugin or project directory. See [.env.example](.env.example).

## Usage

Just ask Claude, for example:

- "Generate a flat icon of a gear and save it as `icons/gear.png`"
- "Edit `hero.png` so the sky is sunset"
- "Make that again in premium quality" (Claude asks before using premium)

Under the hood, the skill runs:

```bash
uv run python main.py --cwd "$PWD" <output_path> "<prompt>" [options]
```

| Option | Short | Description |
|---|---|---|
| `--style` | `-s` | Style template `.md` with a `## Prompt Template` code block |
| `--edit` | `-e` | Edit an existing image (exactly one prompt) |
| `--ref` | `-r` | Reference image (repeatable) |
| `--aspect` | `-a` | `1:1`, `3:2`, `4:3`, `16:9`, `21:9`, `2:3`, `3:4`, `4:5`, `9:16` |
| `--paid` | | Premium tier, requires `--confirm-paid` |
| `--confirm-paid` | | Asserts you confirmed premium usage |

`gpt-image` supports only three sizes (1024x1024, 1536x1024, 1024x1536), so wide ratios such as 16:9 are produced at 3:2. Crop afterwards if you need the exact ratio.

## Exit codes

| Code | Meaning |
|---|---|
| 0 | Image(s) saved |
| 1 | Generation failed (API error or content policy block) |
| 2 | Invalid input (missing file or key, bad template) |
| 3 | Billing, quota, or organization verification problem |

## Development

```bash
uv sync
uv run pytest
```

## License

MIT, see [LICENSE](LICENSE).
