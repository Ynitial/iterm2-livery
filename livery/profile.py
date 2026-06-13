import hashlib
import json
import plistlib
from pathlib import Path

ITERM_PREFS = Path.home() / "Library" / "Preferences" / "com.googlecode.iterm2.plist"

# bg/fg-instellingen die we van het Default-profiel overnemen, zodat livery-tabs
# exact jouw licht/donker-thema volgen (inclusief de "separate colors"-vlag).
INHERITED_KEYS = (
    "Use Separate Colors for Light and Dark Mode",
    "Background Color", "Background Color (Light)", "Background Color (Dark)",
    "Foreground Color", "Foreground Color (Light)", "Foreground Color (Dark)",
)

# iTerm2 Title Components-bitmask: 1 = Session Name. Zo toont de tab precies de
# naam die livery via OSC zet (de mapnaam, evt. met | custom), zonder profielnaam.
TITLE_SESSION_NAME = 1


def default_inherited_settings(prefs_path=ITERM_PREFS):
    """Lees over te nemen instellingen van het iTerm2 default-profiel; {} bij fout."""
    try:
        with open(prefs_path, "rb") as f:
            d = plistlib.load(f)
    except (OSError, ValueError):
        return {}
    guid = d.get("Default Bookmark Guid")
    prof = next((b for b in d.get("New Bookmarks", []) if b.get("Guid") == guid), None)
    if not prof:
        return {}
    return {k: prof[k] for k in INHERITED_KEYS if k in prof}


def profile_guid(root):
    return "livery-" + hashlib.sha1(str(root).encode()).hexdigest()[:16]


def profile_name(root):
    return f"livery: {Path(root).name}"


def profile_file(profiles_dir, root):
    return Path(profiles_dir) / f"{profile_guid(root)}.json"


def _color(rgb):
    r, g, b = (c / 255 for c in rgb)
    return {
        "Red Component": r, "Green Component": g, "Blue Component": b,
        "Alpha Component": 1, "Color Space": "sRGB",
    }


def build_profile(root, icon_path, tab_rgb, color_settings=None):
    profile = {
        "Name": profile_name(root),
        "Guid": profile_guid(root),
        "Dynamic Profile Parent Name": "Default",
        "Icon": 2,
        "Custom Icon Path": str(icon_path),
        "Use Tab Color": True,
        "Tab Color": _color(tab_rgb),
        "Title Components": TITLE_SESSION_NAME,  # tab toont onze sessienaam
    }
    if color_settings:
        profile.update(color_settings)  # neem licht/donker bg+fg van Default over
    return profile


def write_profile(profiles_dir, profile):
    d = Path(profiles_dir)
    d.mkdir(parents=True, exist_ok=True)
    path = d / f"{profile['Guid']}.json"
    path.write_text(json.dumps({"Profiles": [profile]}, indent=2))
