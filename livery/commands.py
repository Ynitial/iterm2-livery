"""Per-commando config voor de wrappers. Eén bron van waarheid, gelezen door
zowel Python (emit) als zsh (wrapper-generatie via `livery commands`)."""
import copy
import json
from pathlib import Path

DEFAULT_COMMANDS = {
    "claude": {"emoji": "🦀", "bg": [240, 156, 132], "fullscreen": True},
    "dev": {"emoji": "👷‍♂️", "bg": [255, 231, 93], "run": "npm run dev"},
    "watch": {"emoji": "👷‍♂️", "bg": [255, 231, 93], "run": "npm run watch"},
}


def load(path):
    # Begin altijd bij een diepe kopie van de defaults, zodat nieuw toegevoegde
    # commando's (bv. dev/watch) ook verschijnen voor gebruikers met een
    # bestaande, oudere commands.json. De gebruiker-config overschrijft per
    # commando-naam; DEFAULT_COMMANDS zelf blijft onaangeroerd (deepcopy).
    merged = copy.deepcopy(DEFAULT_COMMANDS)
    p = Path(path)
    if not p.exists():
        return merged
    try:
        data = json.loads(p.read_text())
    except (OSError, ValueError):
        return merged
    if isinstance(data, dict):
        merged.update(data)
    return merged


def ensure(path):
    p = Path(path)
    if not p.exists():
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(DEFAULT_COMMANDS, indent=2, ensure_ascii=False))
    return load(p)
