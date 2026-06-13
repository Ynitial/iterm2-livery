import hashlib
import json
from pathlib import Path


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


def build_profile(root, icon_path, tab_rgb):
    return {
        "Name": profile_name(root),
        "Guid": profile_guid(root),
        "Dynamic Profile Parent Name": "Default",
        "Icon": 2,
        "Custom Icon Path": str(icon_path),
        "Use Tab Color": True,
        "Tab Color": _color(tab_rgb),
    }


def write_profile(profiles_dir, profile):
    d = Path(profiles_dir)
    d.mkdir(parents=True, exist_ok=True)
    path = d / f"{profile['Guid']}.json"
    path.write_text(json.dumps({"Profiles": [profile]}, indent=2))
