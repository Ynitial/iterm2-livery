"""Claude Code custom-thema voor de Claude-modus: donkere, leesbare tekst op
het oranje + een lichter-oranje achtergrond achter jouw berichten (fullscreen).

Tokennamen volgen de Claude Code theme-referentie; verifieer bij twijfel via
`/theme` in de draaiende versie (onbekende tokens worden genegeerd)."""
import json
from pathlib import Path

SLUG = "livery-claude"

# Lichter oranje (≈30% richting wit) voor userMessageBackground.
_USER_BG = "#E4A089"


def theme_json():
    return {
        "name": SLUG,
        "base": "light",
        "overrides": {
            "text": "#2B1810",
            "inactive": "#7A5142",
            "subtle": "#8A5F4E",
            "claude": "#3A1B0E",
            "success": "#2F5A22",
            "error": "#7A1F12",
            "warning": "#6B4A12",
            "permission": "#243D66",
            "suggestion": "#5C2450",
            "promptBorder": "#3A1B0E",
            "userMessageBackground": _USER_BG,
        },
    }


def write_theme(themes_dir):
    d = Path(themes_dir)
    d.mkdir(parents=True, exist_ok=True)
    path = d / f"{SLUG}.json"
    path.write_text(json.dumps(theme_json(), indent=2, ensure_ascii=False))
    return path


def activate(settings_path):
    p = Path(settings_path)
    data = {}
    if p.exists():
        try:
            data = json.loads(p.read_text())
        except (OSError, ValueError):
            data = {}
    if not isinstance(data, dict):
        data = {}
    data["theme"] = f"custom:{SLUG}"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, indent=2, ensure_ascii=False))
