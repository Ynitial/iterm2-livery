import hashlib
import json
from pathlib import Path


def _hash(root):
    return hashlib.sha1(str(root).encode()).hexdigest()[:16]


def store_path(store_dir, root):
    return Path(store_dir) / f"{_hash(root)}.json"


def read_entry(store_dir, root):
    p = store_path(store_dir, root)
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text())
    except ValueError:
        return None


def write_entry(store_dir, root, entry):
    Path(store_dir).mkdir(parents=True, exist_ok=True)
    store_path(store_dir, root).write_text(json.dumps(entry, indent=2))


def iter_entries(store_dir):
    d = Path(store_dir)
    if not d.exists():
        return
    for f in d.glob("*.json"):
        try:
            yield json.loads(f.read_text())
        except ValueError:
            continue
