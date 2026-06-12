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
