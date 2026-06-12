import json
from pathlib import Path

ENV_KEYS = ("APP_NAME", "PROJECT_NAME", "NAME", "VITE_APP_NAME", "NEXT_PUBLIC_APP_NAME")


def name_from_manifest(manifest_path):
    try:
        data = json.loads(Path(manifest_path).read_text())
    except (OSError, ValueError):
        return None
    for key in ("name", "short_name"):
        val = data.get(key)
        if isinstance(val, str) and val.strip():
            return val.strip()
    return None


def name_from_env(root):
    try:
        lines = (Path(root) / ".env").read_text().splitlines()
    except OSError:
        return None
    values = {}
    for line in lines:
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        values[key.strip()] = val.strip().strip('"').strip("'")
    for key in ENV_KEYS:
        if values.get(key):
            return values[key]
    return None


def base_name(root, manifest_path=None):
    if manifest_path is not None:
        name = name_from_manifest(manifest_path)
        if name:
            return name
    name = name_from_env(root)
    if name:
        return name
    return Path(root).name


def tab_title(base, custom=None):
    return f"{base} | {custom}" if custom else base
