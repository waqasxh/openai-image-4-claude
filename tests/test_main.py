import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import main  # noqa: E402


def test_aspect_sizes_are_supported():
    assert set(main.ASPECT_TO_SIZE.values()) <= {"1024x1024", "1536x1024", "1024x1536"}


def test_style_template_roundtrip(tmp_path):
    f = tmp_path / "s.md"
    f.write_text("## Prompt Template\n```\nA flat icon of [SUBJECT] {x}\n```\n")
    t = main.load_style_template(f)
    assert main.apply_style_template(t, "gear") == "A flat icon of gear {x}"


def test_paid_requires_confirm(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setattr(sys, "argv", ["main.py", "o.png", "x", "--paid"])
    assert main.main() == main.EXIT_BAD_INPUT


def test_missing_key(monkeypatch, tmp_path):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setattr(main, "_load_env", lambda *a: None)
    monkeypatch.setattr(sys, "argv", ["main.py", "o.png", "x", "--cwd", str(tmp_path)])
    assert main.main() == main.EXIT_BAD_INPUT
