"""Per-commando config voor de wrappers. Eén bron van waarheid, gelezen door
zowel Python (emit) als zsh (wrapper-generatie via `livery commands`)."""
import json
from pathlib import Path

DEFAULT_COMMANDS = {
    "claude": {"emoji": "🦀", "bg": [217, 119, 87], "fullscreen": True},
    "dev": {"emoji": "👷‍♂️", "bg": [255, 231, 93], "run": "npm run dev"},
    "watch": {"emoji": "👷‍♂️", "bg": [255, 231, 93], "run": "npm run watch"},
}


def load(path):
    p = Path(path)
    if not p.exists():
        return dict(DEFAULT_COMMANDS)
    try:
        data = json.loads(p.read_text())
    except (OSError, ValueError):
        return dict(DEFAULT_COMMANDS)
    return data if isinstance(data, dict) else dict(DEFAULT_COMMANDS)


def ensure(path):
    p = Path(path)
    if not p.exists():
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(DEFAULT_COMMANDS, indent=2, ensure_ascii=False))
    return load(p)
