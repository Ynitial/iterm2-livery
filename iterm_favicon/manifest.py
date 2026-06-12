import json
import os
from pathlib import Path

PRUNE = {"node_modules", ".git", "dist", "build", "vendor"}
MANIFEST_NAME = "site.webmanifest"


def find_manifest(root, maxdepth=6, prune=PRUNE):
    """Recursief omlaag vanaf root; eerste site.webmanifest (deterministisch)."""
    root = Path(root)
    base_depth = len(root.resolve().parts)
    for dirpath, dirnames, filenames in os.walk(root):
        depth = len(Path(dirpath).resolve().parts) - base_depth
        dirnames[:] = sorted(d for d in dirnames if d not in prune)
        if depth >= maxdepth:
            dirnames[:] = []
        if MANIFEST_NAME in filenames:
            return Path(dirpath) / MANIFEST_NAME
    return None


def resolve_src(manifest_path, src):
    base = Path(manifest_path).parent
    rel = src[1:] if src.startswith("/") else src
    return (base / rel).resolve()


def first_png(manifest_path):
    """Eerste icon met een .png-src, als absoluut pad; None bij fout/afwezig."""
    try:
        data = json.loads(Path(manifest_path).read_text())
    except (OSError, ValueError):
        return None
    for icon in data.get("icons", []):
        src = icon.get("src", "")
        if isinstance(src, str) and src.lower().endswith(".png"):
            return resolve_src(manifest_path, src)
    return None
