import json
import subprocess
from pathlib import Path

PRUNE = ("node_modules", ".git", "dist", "build", "vendor")
MANIFEST_NAME = "site.webmanifest"
WEB_DIRS = ("", "public", "static", "www")  # "" = de root zelf


def _targeted(root):
    """Conventionele plekken (root + web-submappen); alles losse stats, snel."""
    for sub in WEB_DIRS:
        cand = (root / sub / MANIFEST_NAME) if sub else (root / MANIFEST_NAME)
        if cand.is_file():
            return cand
    return None


def find_manifest(root, maxdepth=6):
    """Eerst conventionele plekken; daarna recursief mits er een .git is.

    Een niet-git-map (zoals ~ of /tmp) wordt NOOIT recursief afgestruind — dat
    voorkomt trage scans en spook-treffers van willekeurige geneste projecten.
    """
    root = Path(root)
    hit = _targeted(root)
    if hit is not None:
        return hit
    if not (root / ".git").exists():
        return None
    prune = []
    for name in PRUNE:
        prune += ["-name", name, "-o"]
    cmd = ["find", str(root), "-maxdepth", str(maxdepth),
           "(", *prune[:-1], ")", "-prune", "-o",
           "-name", MANIFEST_NAME, "-print", "-quit"]
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
    except (OSError, subprocess.SubprocessError):
        return None
    line = out.stdout.strip().splitlines()
    return Path(line[0]) if line else None


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
