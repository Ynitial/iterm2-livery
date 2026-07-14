"""Claude Code custom-thema voor de Claude-modus: lichte, leesbare tekst op de
donkerblauwe claude-achtergrond (#18242C) + een iets lichter-blauw vlak
achter jouw berichten (fullscreen).

Tokennamen volgen de Claude Code theme-referentie; verifieer bij twijfel via
`/theme` in de draaiende versie (onbekende tokens worden genegeerd). Omdat de
achtergrond donker is, gebruikt dit thema `base: dark` met lichte tokens —
het donkere ANSI-palet uit `palette` past hier niet, dus de kleuren zijn
theme-specifiek en letterlijk."""
import json
from pathlib import Path

SLUG = "livery-claude"

# Iets lichter dan de claude-achtergrond (#18242C) voor userMessageBackground,
# zodat jouw eigen berichten een zacht opgelicht vlak krijgen.
_USER_BG = "#1F2D37"


def theme_json():
    return {
        "name": SLUG,
        "base": "dark",
        "overrides": {
            "text": "#F3E7E0",
            "inactive": "#B39B8E",
            "subtle": "#A2897C",
            "claude": "#F0B99E",
            "success": "#9FCF7F",
            "error": "#F09A88",
            "warning": "#E6B95F",
            "permission": "#9EB8E8",
            "suggestion": "#D0A6C8",
            "promptBorder": "#F0B99E",
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
