# Claude Desktop — config persistence
# Victorious Framework | Origin Source Labs

import json
import os
from pathlib import Path

CONFIG_DIR = Path.home() / ".config" / "claude-desktop"
CONFIG_FILE = CONFIG_DIR / "config.json"

DEFAULTS = {
    "api_key": "",
    "model": "claude-opus-4-8",
    "system_prompt": "You are a helpful assistant.",
    "thinking": True,
    "effort": "high",
    "max_tokens": 16000,
    "window_width": 1100,
    "window_height": 760,
}

MODELS = [
    ("Claude Opus 4.8  (most capable)", "claude-opus-4-8"),
    ("Claude Sonnet 4.6  (balanced)", "claude-sonnet-4-6"),
    ("Claude Haiku 4.5  (fastest)", "claude-haiku-4-5"),
]

EFFORT_LEVELS = ["low", "medium", "high", "xhigh", "max"]


def load() -> dict:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    if CONFIG_FILE.exists():
        try:
            data = json.loads(CONFIG_FILE.read_text())
            return {**DEFAULTS, **data}
        except Exception:
            pass
    return dict(DEFAULTS)


def save(cfg: dict) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(json.dumps(cfg, indent=2))
