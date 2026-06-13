# livery Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Een zsh-schil rond iTerm2 die per project-root automatisch de favicon (uit `site.webmanifest`) als tab-icoon zet plus een subtiel gemute tint op tab + terminal-achtergrond, opgeslagen in een persistente per-root store.

**Architecture:** Een dunne zsh-laag (`chpwd`/startup hook + `livery` commando) roept een Python-pakket aan. Het Python-pakket leest een persistente store als bron van waarheid; alleen bij eerste detectie, `scan` of `set-icon` doet het de dure afleiding (manifest zoeken → eerste PNG → dominante kleur via `sips`→BMP). Een Dynamic Profile per root draagt het icoon + de kleuren; switchen gebeurt via een `SetProfile`-escape-code.

**Tech Stack:** zsh, Python 3 (stdlib only: `json`, `os`, `pathlib`, `struct`, `zlib`, `hashlib`, `subprocess`, `argparse`, `collections`), macOS `sips` + `defaults`, iTerm2 Dynamic Profiles. Tests met `pytest`.

---

## File Structure

```
~/projects/livery/
├── livery.zsh              # zsh-laag: hook + `livery` commando
├── livery/                 # Python-pakket (python3 livery <cmd>)
│   ├── __init__.py
│   ├── __main__.py                # argparse-dispatch: emit/scan/set-icon/clean
│   ├── roots.py                   # find_project_root(cwd)
│   ├── manifest.py                # find_manifest, first_png, resolve_src
│   ├── color.py                   # read_bmp, sips_pixels, dominant_color, average_color
│   ├── tint.py                    # detect_theme, mute
│   ├── store.py                   # store_path, read_entry, write_entry, iter_entries
│   ├── profile.py                 # build_profile, write_profile, profile_file, profile_name, profile_guid
│   ├── escapes.py                 # OSC-sequence strings
│   └── app.py                     # orchestratie: cmd_emit/cmd_scan/cmd_set_icon/cmd_clean
├── tests/
│   ├── conftest.py                # make_png fixture-helper
│   ├── test_roots.py
│   ├── test_manifest.py
│   ├── test_color.py
│   ├── test_tint.py
│   ├── test_store.py
│   ├── test_profile.py
│   ├── test_escapes.py
│   └── test_app.py
├── docs/superpowers/{specs,plans}/
├── ITERM2-KEYS.md                 # output van Taak 0 (geverifieerde sleutels)
└── README.md
```

Eén verantwoordelijkheid per bestand. `app.py` bevat de enige plek die de modules aan elkaar knoopt; alle andere modules zijn pure, los-testbare functies.

---

## Task 0: Verifieer iTerm2 Dynamic-Profile-sleutels (handmatig)

Dit bevestigt de exacte JSON-sleutels voordat we code schrijven die ervan afhangt. Het verwachte resultaat is `"Icon": 2` + `"Custom Icon Path"`, maar we bevestigen het tegen een echt profiel.

**Files:**
- Create: `ITERM2-KEYS.md`

- [ ] **Step 1: Maak een testprofiel met custom icoon in iTerm2**

Open iTerm2 → Settings (⌘,) → Profiles → `+` (nieuw profiel, noem het `keytest`) → tab **General** → onderaan **Icon** → kies **Custom** → selecteer een willekeurige PNG. Sluit Settings.

- [ ] **Step 2: Lees de echte sleutels uit de preferences**

Run:
```bash
plutil -convert json -o - ~/Library/Preferences/com.googlecode.iterm2.plist \
  | python3 -c 'import json,sys; d=json.load(sys.stdin); \
print(json.dumps([p for p in d["New Bookmarks"] if p.get("Name")=="keytest"][0], indent=2))' \
  | grep -iE "icon|tab color|background color|use tab"
```
Expected: regels met `"Icon": 2`, `"Custom Icon Path": "<jouw pad>"`. (Als de getalwaarde of sleutelnaam afwijkt, noteer de echte waarde.)

- [ ] **Step 3: Leg de bevestigde sleutels vast**

Maak `ITERM2-KEYS.md` met de daadwerkelijk waargenomen sleutels en waarden, bijv.:
```markdown
# Geverifieerde iTerm2 Dynamic-Profile-sleutels (2026-06-12)
- Icon-modus:        "Icon": 2        # 2 = custom
- Icoon-pad:         "Custom Icon Path": "<abs pad naar .png>"
- Tabkleur aan:      "Use Tab Color": true
- Tabkleur:          "Tab Color": {Red/Green/Blue/Alpha Component (0-1), "Color Space":"sRGB"}
- Achtergrondkleur:  "Background Color": { ... zelfde vorm ... }
- Dynamic profiles:  bestand = {"Profiles": [ <profiel> ]}, map = ~/Library/Application Support/iTerm2/DynamicProfiles/
```
**Als een sleutel/waarde afwijkt van bovenstaande, pas `livery/profile.py` in Taak 9 daarop aan.** Verwijder daarna het `keytest`-profiel.

- [ ] **Step 4: Commit**

```bash
cd ~/projects/livery
git add ITERM2-KEYS.md
git commit -m "docs: verified iTerm2 dynamic profile keys"
```

---

## Task 1: Projectopzet + test-harness

**Files:**
- Create: `livery/__init__.py`, `livery/__main__.py`, `tests/conftest.py`, `pyproject.toml`

- [ ] **Step 1: Maak een leeg pakket + pytest-config**

Create `livery/__init__.py`:
```python
"""livery: per-project iTerm2 tab icon + muted color tint."""
```

Create `pyproject.toml`:
```toml
[tool.pytest.ini_options]
pythonpath = ["."]
testpaths = ["tests"]
```

- [ ] **Step 2: Maak de PNG-fixture-helper**

Create `tests/conftest.py`:
```python
import struct
import zlib
from pathlib import Path

import pytest


def _make_png(path, rgb, w=16, h=16):
    """Schrijf een geldige 8-bit RGB PNG van w×h in één effen kleur."""
    def chunk(typ, data):
        body = typ + data
        return struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body) & 0xFFFFFFFF)

    sig = b"\x89PNG\r\n\x1a\n"
    ihdr = struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)  # 8-bit, color type 2 (RGB)
    row = b"\x00" + (bytes(rgb) * w)                     # filter byte 0 + pixels
    idat = zlib.compress(row * h)
    Path(path).write_bytes(sig + chunk(b"IHDR", ihdr) + chunk(b"IDAT", idat) + chunk(b"IEND", b""))


@pytest.fixture
def make_png():
    return _make_png
```

- [ ] **Step 3: Verifieer dat pytest draait (nog 0 tests)**

Run: `cd ~/projects/livery && python3 -m pytest -q`
Expected: `no tests ran` (exit 5) — pytest werkt, conftest importeert zonder fouten.

- [ ] **Step 4: Commit**

```bash
git add pyproject.toml livery/__init__.py tests/conftest.py
git commit -m "chore: project scaffolding and PNG test fixture"
```

---

## Task 2: Project-root bepalen

**Files:**
- Create: `livery/roots.py`, `tests/test_roots.py`

- [ ] **Step 1: Schrijf de falende test**

Create `tests/test_roots.py`:
```python
from pathlib import Path

from livery.roots import find_project_root


def test_walks_up_to_git_dir(tmp_path):
    (tmp_path / ".git").mkdir()
    sub = tmp_path / "src" / "components"
    sub.mkdir(parents=True)
    assert find_project_root(sub) == tmp_path.resolve()


def test_falls_back_to_cwd_without_git(tmp_path):
    sub = tmp_path / "a" / "b"
    sub.mkdir(parents=True)
    assert find_project_root(sub) == sub.resolve()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_roots.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'livery.roots'`

- [ ] **Step 3: Implementeer**

Create `livery/roots.py`:
```python
from pathlib import Path


def find_project_root(cwd):
    """Loop omhoog tot de eerste map met .git; anders de cwd zelf."""
    start = Path(cwd).resolve()
    for d in (start, *start.parents):
        if (d / ".git").exists():
            return d
    return start
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_roots.py -q`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add livery/roots.py tests/test_roots.py
git commit -m "feat: project root resolution via .git walk-up"
```

---

## Task 3: Manifest zoeken

**Files:**
- Create: `livery/manifest.py`, `tests/test_manifest.py`

- [ ] **Step 1: Schrijf de falende test**

Create `tests/test_manifest.py`:
```python
from pathlib import Path

from livery.manifest import find_manifest


def test_finds_manifest_in_subdir(tmp_path):
    pub = tmp_path / "public"
    pub.mkdir()
    m = pub / "site.webmanifest"
    m.write_text("{}")
    assert find_manifest(tmp_path) == m


def test_prunes_node_modules(tmp_path):
    nm = tmp_path / "node_modules" / "pkg"
    nm.mkdir(parents=True)
    (nm / "site.webmanifest").write_text("{}")
    assert find_manifest(tmp_path) is None


def test_respects_maxdepth(tmp_path):
    deep = tmp_path / "a" / "b" / "c"
    deep.mkdir(parents=True)
    (deep / "site.webmanifest").write_text("{}")
    assert find_manifest(tmp_path, maxdepth=1) is None
    assert find_manifest(tmp_path, maxdepth=6) == deep / "site.webmanifest"


def test_returns_none_when_absent(tmp_path):
    assert find_manifest(tmp_path) is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_manifest.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'livery.manifest'`

- [ ] **Step 3: Implementeer (gedeeltelijk — alleen find_manifest)**

Create `livery/manifest.py`:
```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_manifest.py -q`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
git add livery/manifest.py tests/test_manifest.py
git commit -m "feat: recursive site.webmanifest discovery with prune + maxdepth"
```

---

## Task 4: Eerste PNG uit het manifest + pad-resolutie

**Files:**
- Modify: `livery/manifest.py`
- Modify: `tests/test_manifest.py`

- [ ] **Step 1: Schrijf de falende test (toevoegen aan bestand)**

Append to `tests/test_manifest.py`:
```python
from livery.manifest import first_png


def test_first_png_relative_src(tmp_path):
    m = tmp_path / "site.webmanifest"
    m.write_text('{"icons":[{"src":"icons/a.png"}]}')
    assert first_png(m) == (tmp_path / "icons" / "a.png").resolve()


def test_first_png_web_absolute_src(tmp_path):
    m = tmp_path / "site.webmanifest"
    m.write_text('{"icons":[{"src":"/android-chrome-192.png"}]}')
    assert first_png(m) == (tmp_path / "android-chrome-192.png").resolve()


def test_first_png_skips_non_png(tmp_path):
    m = tmp_path / "site.webmanifest"
    m.write_text('{"icons":[{"src":"a.svg"},{"src":"b.png"}]}')
    assert first_png(m) == (tmp_path / "b.png").resolve()


def test_first_png_none_when_no_png(tmp_path):
    m = tmp_path / "site.webmanifest"
    m.write_text('{"icons":[{"src":"a.svg"}]}')
    assert first_png(m) is None


def test_first_png_invalid_json(tmp_path):
    m = tmp_path / "site.webmanifest"
    m.write_text("{ not json")
    assert first_png(m) is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_manifest.py -q`
Expected: FAIL — `ImportError: cannot import name 'first_png'`

- [ ] **Step 3: Implementeer (toevoegen aan manifest.py)**

Append to `livery/manifest.py`:
```python
import json


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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_manifest.py -q`
Expected: PASS (9 passed)

- [ ] **Step 5: Commit**

```bash
git add livery/manifest.py tests/test_manifest.py
git commit -m "feat: extract first PNG icon from manifest with path resolution"
```

---

## Task 5: Kleur — BMP lezen, gemiddelde en dominant

**Files:**
- Create: `livery/color.py`, `tests/test_color.py`

- [ ] **Step 1: Schrijf de falende test (pure functies, geen sips)**

Create `tests/test_color.py`:
```python
import struct

from livery.color import average_color, dominant_color, read_bmp


def _bmp(pixels, w, h):
    """Bouw een minimale 24-bit BMP. pixels = lijst van (r,g,b), rij-voor-rij top-down."""
    row_size = (w * 3 + 3) & ~3
    pad = row_size - w * 3
    pixel_data = b""
    for row in range(h - 1, -1, -1):  # BMP is bottom-up
        for x in range(w):
            r, g, b = pixels[row * w + x]
            pixel_data += bytes((b, g, r))
        pixel_data += b"\x00" * pad
    offset = 54
    header = b"BM" + struct.pack("<IHHI", offset + len(pixel_data), 0, 0, offset)
    info = struct.pack("<IiiHHIIiiII", 40, w, h, 1, 24, 0, len(pixel_data), 2835, 2835, 0, 0)
    return header + info + pixel_data


def test_read_bmp_roundtrip():
    pixels = [(255, 0, 0), (0, 255, 0), (0, 0, 255), (10, 20, 30)]
    assert read_bmp(_bmp(pixels, 2, 2)) == pixels


def test_average_color():
    assert average_color([(0, 0, 0), (100, 200, 50)]) == (50, 100, 25)


def test_dominant_ignores_white_and_black():
    # 6 witte, 6 zwarte, 4 blauwe pixels -> dominant moet blauw zijn
    pixels = [(255, 255, 255)] * 6 + [(0, 0, 0)] * 6 + [(20, 40, 200)] * 4
    assert dominant_color(pixels) == (20, 40, 200)


def test_dominant_falls_back_to_average_when_all_extreme():
    pixels = [(255, 255, 255)] * 4 + [(0, 0, 0)] * 4
    # alles is extreem -> gemiddelde
    assert dominant_color(pixels) == average_color(pixels)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_color.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'livery.color'`

- [ ] **Step 3: Implementeer de pure functies**

Create `livery/color.py`:
```python
import struct
from collections import Counter

NEAR = 24  # drempel voor "bijna zwart/wit"


def read_bmp(data):
    """Lees een ongecomprimeerde 24-bit BMP -> lijst (r,g,b), top-down rij-volgorde."""
    pixel_offset = struct.unpack_from("<I", data, 10)[0]
    width = struct.unpack_from("<i", data, 18)[0]
    height = struct.unpack_from("<i", data, 22)[0]
    bpp = struct.unpack_from("<H", data, 28)[0]
    if bpp != 24:
        raise ValueError(f"verwacht 24-bit BMP, kreeg {bpp}")
    bottom_up = height > 0
    h = abs(height)
    row_size = (width * 3 + 3) & ~3
    out = []
    for row in range(h):
        src = (h - 1 - row) if bottom_up else row
        base = pixel_offset + src * row_size
        for x in range(width):
            b = data[base + x * 3]
            g = data[base + x * 3 + 1]
            r = data[base + x * 3 + 2]
            out.append((r, g, b))
    return out


def average_color(pixels):
    n = len(pixels)
    return tuple(sum(p[i] for p in pixels) // n for i in range(3))


def _extreme(p):
    return all(c <= NEAR for c in p) or all(c >= 255 - NEAR for c in p)


def dominant_color(pixels):
    """Meest voorkomende gequantiseerde niet-extreme kleur; anders gemiddelde."""
    candidates = [p for p in pixels if not _extreme(p)]
    if not candidates:
        return average_color(pixels)
    counts = Counter(tuple(c >> 4 for c in p) for p in candidates)
    winner = counts.most_common(1)[0][0]
    members = [p for p in candidates if tuple(c >> 4 for c in p) == winner]
    return average_color(members)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_color.py -q`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
git add livery/color.py tests/test_color.py
git commit -m "feat: BMP reader + average and dominant color"
```

---

## Task 6: Kleur — sips-integratie (PNG → pixels)

**Files:**
- Modify: `livery/color.py`
- Modify: `tests/test_color.py`

- [ ] **Step 1: Schrijf de falende integratietest (gebruikt echte sips + make_png)**

Append to `tests/test_color.py`:
```python
import shutil

import pytest

from livery.color import sips_pixels, color_from_png


sips_available = pytest.mark.skipif(shutil.which("sips") is None, reason="sips ontbreekt")


@sips_available
def test_sips_pixels_solid_red(make_png, tmp_path):
    png = tmp_path / "red.png"
    make_png(png, (220, 30, 40), w=32, h=32)
    pixels = sips_pixels(png, 8)
    assert len(pixels) == 64
    r, g, b = pixels[0]
    assert r > 150 and g < 90 and b < 90  # ruwweg rood na herschaling


@sips_available
def test_color_from_png_solid(make_png, tmp_path):
    png = tmp_path / "blue.png"
    make_png(png, (30, 60, 210), w=32, h=32)
    r, g, b = color_from_png(png)
    assert b > 150 and b > r and b > g
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_color.py -q`
Expected: FAIL — `ImportError: cannot import name 'sips_pixels'`

- [ ] **Step 3: Implementeer (toevoegen aan color.py)**

Append to `livery/color.py`:
```python
import os
import subprocess
import tempfile
from pathlib import Path

DOMINANT_SIZE = 16


def sips_pixels(png_path, size):
    """Schaal de PNG naar size×size via sips, lever BMP-pixels (r,g,b)."""
    with tempfile.TemporaryDirectory() as td:
        out = os.path.join(td, "o.bmp")
        subprocess.run(
            ["sips", "-s", "format", "bmp", "-z", str(size), str(size),
             str(png_path), "--out", out],
            check=True, capture_output=True,
        )
        return read_bmp(Path(out).read_bytes())


def color_from_png(png_path):
    """Dominante kleur van een PNG; valt terug op None bij sips/decode-fout."""
    try:
        pixels = sips_pixels(png_path, DOMINANT_SIZE)
    except (subprocess.CalledProcessError, ValueError, OSError):
        return None
    return dominant_color(pixels)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_color.py -q`
Expected: PASS (6 passed). (Als `sips` niet bestaat: 2 skipped — acceptabel op niet-macOS.)

- [ ] **Step 5: Commit**

```bash
git add livery/color.py tests/test_color.py
git commit -m "feat: sips-based PNG-to-color pipeline"
```

---

## Task 7: Thema-detectie + gemute tint

**Files:**
- Create: `livery/tint.py`, `tests/test_tint.py`

- [ ] **Step 1: Schrijf de falende test**

Create `tests/test_tint.py`:
```python
from livery.tint import mute


def test_mute_dark_blends_to_black():
    # 50% van (200,100,50) richting zwart
    assert mute((200, 100, 50), "dark", 0.5) == (100, 50, 25)


def test_mute_light_blends_to_white():
    # 0% kleur -> volledig wit
    assert mute((10, 20, 30), "light", 0.0) == (255, 255, 255)


def test_mute_full_strength_is_color():
    assert mute((10, 20, 30), "dark", 1.0) == (10, 20, 30)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_tint.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'livery.tint'`

- [ ] **Step 3: Implementeer**

Create `livery/tint.py`:
```python
import subprocess


def detect_theme():
    """'dark' als macOS in dark mode staat, anders 'light'."""
    try:
        r = subprocess.run(
            ["defaults", "read", "-g", "AppleInterfaceStyle"],
            capture_output=True, text=True,
        )
    except OSError:
        return "light"
    return "dark" if r.returncode == 0 and "Dark" in r.stdout else "light"


def mute(color, theme, strength):
    """Blend color richting de thema-achtergrond. strength 1.0 = pure kleur."""
    bg = (0, 0, 0) if theme == "dark" else (255, 255, 255)
    return tuple(round(c * strength + b * (1 - strength)) for c, b in zip(color, bg))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_tint.py -q`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add livery/tint.py tests/test_tint.py
git commit -m "feat: macOS theme detection + muted tint blend"
```

---

## Task 8: Per-root store

**Files:**
- Create: `livery/store.py`, `tests/test_store.py`

- [ ] **Step 1: Schrijf de falende test**

Create `tests/test_store.py`:
```python
from livery.store import iter_entries, read_entry, store_path, write_entry


def test_write_then_read(tmp_path):
    entry = {"root": "/x", "icon_path": "/x/a.png",
             "dominant_color": [10, 20, 30], "source": "manifest", "last_theme": "dark"}
    write_entry(tmp_path, "/x", entry)
    assert read_entry(tmp_path, "/x") == entry


def test_read_missing_returns_none(tmp_path):
    assert read_entry(tmp_path, "/nope") is None


def test_store_path_stable_per_root(tmp_path):
    assert store_path(tmp_path, "/x") == store_path(tmp_path, "/x")
    assert store_path(tmp_path, "/x") != store_path(tmp_path, "/y")


def test_iter_entries(tmp_path):
    write_entry(tmp_path, "/a", {"root": "/a"})
    write_entry(tmp_path, "/b", {"root": "/b"})
    roots = sorted(e["root"] for e in iter_entries(tmp_path))
    assert roots == ["/a", "/b"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_store.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'livery.store'`

- [ ] **Step 3: Implementeer**

Create `livery/store.py`:
```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_store.py -q`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
git add livery/store.py tests/test_store.py
git commit -m "feat: persistent per-root store"
```

---

## Task 9: Dynamic Profile-generatie

**Files:**
- Create: `livery/profile.py`, `tests/test_profile.py`

> Gebruik de in **Taak 0** bevestigde sleutels. Onderstaande code gaat uit van
> `"Icon": 2` + `"Custom Icon Path"`; pas aan als Taak 0 afweek.

- [ ] **Step 1: Schrijf de falende test**

Create `tests/test_profile.py`:
```python
import json

from livery.profile import (
    build_profile, profile_file, profile_guid, profile_name, write_profile,
)


def test_profile_name_uses_root_basename():
    assert profile_name("/Users/yoni/projects/slowboard") == "livery: slowboard"


def test_guid_stable_per_root():
    assert profile_guid("/x") == profile_guid("/x")
    assert profile_guid("/x") != profile_guid("/y")


def test_build_profile_has_icon_and_colors():
    p = build_profile("/x/proj", "/x/proj/a.png", (255, 0, 0), (10, 10, 10))
    assert p["Icon"] == 2
    assert p["Custom Icon Path"] == "/x/proj/a.png"
    assert p["Use Tab Color"] is True
    assert p["Dynamic Profile Parent Name"] == "Default"
    assert abs(p["Tab Color"]["Red Component"] - 1.0) < 1e-6
    assert abs(p["Background Color"]["Red Component"] - 10 / 255) < 1e-6


def test_write_profile_wraps_in_profiles_array(tmp_path):
    p = build_profile("/x/proj", "/x/proj/a.png", (1, 2, 3), (4, 5, 6))
    write_profile(tmp_path, p)
    written = json.loads(profile_file(tmp_path, "/x/proj").read_text())
    assert written["Profiles"][0]["Guid"] == p["Guid"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_profile.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'livery.profile'`

- [ ] **Step 3: Implementeer**

Create `livery/profile.py`:
```python
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


def build_profile(root, icon_path, tab_rgb, bg_rgb):
    return {
        "Name": profile_name(root),
        "Guid": profile_guid(root),
        "Dynamic Profile Parent Name": "Default",
        "Icon": 2,
        "Custom Icon Path": str(icon_path),
        "Use Tab Color": True,
        "Tab Color": _color(tab_rgb),
        "Background Color": _color(bg_rgb),
    }


def write_profile(profiles_dir, profile):
    d = Path(profiles_dir)
    d.mkdir(parents=True, exist_ok=True)
    path = d / f"{profile['Guid']}.json"
    path.write_text(json.dumps({"Profiles": [profile]}, indent=2))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_profile.py -q`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
git add livery/profile.py tests/test_profile.py
git commit -m "feat: iTerm2 dynamic profile generation"
```

---

## Task 10: Escape-sequences

**Files:**
- Create: `livery/escapes.py`, `tests/test_escapes.py`

- [ ] **Step 1: Schrijf de falende test**

Create `tests/test_escapes.py`:
```python
from livery.escapes import set_profile, tab_color, reset


def test_set_profile():
    assert set_profile("livery: x") == "\033]1337;SetProfile=livery: x\007"


def test_tab_color_three_channels():
    s = tab_color((10, 20, 30))
    assert s == ("\033]6;1;bg;red;brightness;10\007"
                 "\033]6;1;bg;green;brightness;20\007"
                 "\033]6;1;bg;blue;brightness;30\007")


def test_reset_switches_to_default_and_clears_color():
    assert reset() == "\033]1337;SetProfile=Default\007\033]6;1;bg;*;default\007"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_escapes.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'livery.escapes'`

- [ ] **Step 3: Implementeer**

Create `livery/escapes.py`:
```python
ESC = "\033"
BEL = "\007"


def set_profile(name):
    return f"{ESC}]1337;SetProfile={name}{BEL}"


def tab_color(rgb):
    r, g, b = rgb
    return (f"{ESC}]6;1;bg;red;brightness;{r}{BEL}"
            f"{ESC}]6;1;bg;green;brightness;{g}{BEL}"
            f"{ESC}]6;1;bg;blue;brightness;{b}{BEL}")


def reset():
    return f"{set_profile('Default')}{ESC}]6;1;bg;*;default{BEL}"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_escapes.py -q`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add livery/escapes.py tests/test_escapes.py
git commit -m "feat: OSC escape sequences for profile + tab color"
```

---

## Task 11: Orchestratie — `emit`

**Files:**
- Create: `livery/app.py`, `tests/test_app.py`

`app.py` knoopt alle modules samen. Strengtes komen uit env-vars met defaults.

- [ ] **Step 1: Schrijf de falende test**

Create `tests/test_app.py`:
```python
from livery import app, store
from livery.profile import profile_file


def _dirs(tmp_path):
    return {"profiles_dir": tmp_path / "profiles", "store_dir": tmp_path / "store"}


def test_emit_no_manifest_returns_reset(tmp_path, monkeypatch):
    monkeypatch.setattr(app, "detect_theme", lambda: "dark")
    out = app.cmd_emit(cwd=tmp_path, **_dirs(tmp_path))
    assert out == app.escapes.reset()


def test_emit_detects_and_caches(tmp_path, make_png, monkeypatch):
    monkeypatch.setattr(app, "detect_theme", lambda: "dark")
    monkeypatch.setattr(app, "color_from_png", lambda p: (40, 80, 200))
    (tmp_path / "site.webmanifest").write_text('{"icons":[{"src":"a.png"}]}')
    make_png(tmp_path / "a.png", (40, 80, 200))
    d = _dirs(tmp_path)

    out = app.cmd_emit(cwd=tmp_path, **d)

    assert "SetProfile=livery:" in out
    entry = store.read_entry(d["store_dir"], tmp_path.resolve())
    assert entry["dominant_color"] == [40, 80, 200]
    assert entry["source"] == "manifest"
    assert profile_file(d["profiles_dir"], tmp_path.resolve()).exists()


def test_emit_uses_store_without_rescanning(tmp_path, make_png, monkeypatch):
    monkeypatch.setattr(app, "detect_theme", lambda: "dark")
    d = _dirs(tmp_path)
    icon = tmp_path / "a.png"
    make_png(icon, (40, 80, 200))
    store.write_entry(d["store_dir"], tmp_path.resolve(), {
        "root": str(tmp_path.resolve()), "icon_path": str(icon),
        "dominant_color": [40, 80, 200], "source": "manifest", "last_theme": "dark",
    })

    def boom(_):
        raise AssertionError("color_from_png mag niet draaien op het snelpad")

    monkeypatch.setattr(app, "color_from_png", boom)
    out = app.cmd_emit(cwd=tmp_path, **d)
    assert "SetProfile=livery:" in out


def test_emit_missing_icon_file_resets(tmp_path, monkeypatch):
    monkeypatch.setattr(app, "detect_theme", lambda: "dark")
    d = _dirs(tmp_path)
    store.write_entry(d["store_dir"], tmp_path.resolve(), {
        "root": str(tmp_path.resolve()), "icon_path": str(tmp_path / "gone.png"),
        "dominant_color": [1, 2, 3], "source": "manifest", "last_theme": "dark",
    })
    out = app.cmd_emit(cwd=tmp_path, **d)
    assert out == app.escapes.reset()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_app.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'livery.app'`

- [ ] **Step 3: Implementeer `app.py` (emit + helpers)**

Create `livery/app.py`:
```python
import os
from pathlib import Path

from livery import escapes, store
from livery.color import color_from_png
from livery.manifest import find_manifest, first_png
from livery.profile import build_profile, profile_file, profile_name, write_profile
from livery.roots import find_project_root
from livery.tint import detect_theme, mute

DEFAULT_STORE = Path.home() / ".config" / "livery" / "dirs"
DEFAULT_PROFILES = Path.home() / "Library" / "Application Support" / "iTerm2" / "DynamicProfiles"


def _tab_strength():
    return float(os.environ.get("LIVERY_TAB_STRENGTH", "0.15"))


def _bg_strength():
    return float(os.environ.get("LIVERY_BG_STRENGTH", "0.07"))


def _maxdepth():
    return int(os.environ.get("LIVERY_MAXDEPTH", "6"))


def _ensure_profile(profiles_dir, root, icon_path, rgb, theme):
    tab = mute(rgb, theme, _tab_strength())
    bg = mute(rgb, theme, _bg_strength())
    write_profile(profiles_dir, build_profile(root, icon_path, tab, bg))


def _emit_for(root, rgb, theme):
    tab = mute(rgb, theme, _tab_strength())
    return escapes.set_profile(profile_name(root)) + escapes.tab_color(tab)


def cmd_emit(cwd, profiles_dir, store_dir):
    root = find_project_root(cwd)
    theme = detect_theme()
    entry = store.read_entry(store_dir, root)

    if entry is None:
        png = _autodetect(root)
        if png is None:
            return escapes.reset()
        rgb = color_from_png(png)
        if rgb is None:
            return escapes.reset()
        entry = {"root": str(root), "icon_path": str(png),
                 "dominant_color": list(rgb), "source": "manifest", "last_theme": theme}
        store.write_entry(store_dir, root, entry)
        _ensure_profile(profiles_dir, root, png, rgb, theme)
        return _emit_for(root, rgb, theme)

    icon = Path(entry["icon_path"])
    if not icon.exists():
        return escapes.reset()
    rgb = tuple(entry["dominant_color"])
    if entry.get("last_theme") != theme or not profile_file(profiles_dir, root).exists():
        _ensure_profile(profiles_dir, root, icon, rgb, theme)
        entry["last_theme"] = theme
        store.write_entry(store_dir, root, entry)
    return _emit_for(root, rgb, theme)


def _autodetect(root):
    manifest = find_manifest(root, maxdepth=_maxdepth())
    if manifest is None:
        return None
    png = first_png(manifest)
    if png is None or not Path(png).exists():
        return None
    return png
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_app.py -q`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
git add livery/app.py tests/test_app.py
git commit -m "feat: emit orchestration with store fast-path"
```

---

## Task 12: `scan`, `set-icon`, `clean`

**Files:**
- Modify: `livery/app.py`
- Modify: `livery/store.py`
- Modify: `tests/test_app.py`

- [ ] **Step 1: Schrijf de falende test (toevoegen)**

Append to `tests/test_app.py`:
```python
def test_scan_overwrites_entry(tmp_path, make_png, monkeypatch):
    monkeypatch.setattr(app, "detect_theme", lambda: "dark")
    d = _dirs(tmp_path)
    (tmp_path / "site.webmanifest").write_text('{"icons":[{"src":"a.png"}]}')
    make_png(tmp_path / "a.png", (10, 10, 200))
    store.write_entry(d["store_dir"], tmp_path.resolve(), {
        "root": str(tmp_path.resolve()), "icon_path": "/old.png",
        "dominant_color": [1, 1, 1], "source": "manifest", "last_theme": "dark",
    })
    monkeypatch.setattr(app, "color_from_png", lambda p: (10, 10, 200))
    app.cmd_scan(cwd=tmp_path, **d)
    entry = store.read_entry(d["store_dir"], tmp_path.resolve())
    assert entry["dominant_color"] == [10, 10, 200]
    assert entry["icon_path"].endswith("a.png")


def test_set_icon_sets_manual_source(tmp_path, make_png, monkeypatch):
    d = _dirs(tmp_path)
    icon = tmp_path / "logo.png"
    make_png(icon, (200, 10, 10))
    monkeypatch.setattr(app, "color_from_png", lambda p: (200, 10, 10))
    app.cmd_set_icon(str(icon), cwd=tmp_path, **d)
    entry = store.read_entry(d["store_dir"], tmp_path.resolve())
    assert entry["source"] == "manual"
    assert entry["icon_path"] == str(icon)
    assert entry["dominant_color"] == [200, 10, 10]


def test_clean_removes_orphan_entries(tmp_path):
    d = _dirs(tmp_path)
    gone = tmp_path / "gone"
    alive = tmp_path / "alive"
    alive.mkdir()
    for root in (gone, alive):
        store.write_entry(d["store_dir"], root.resolve(), {"root": str(root.resolve())})
        app._ensure_profile(d["profiles_dir"], root.resolve(), "x.png", (1, 2, 3), "dark")
    removed = app.cmd_clean(**d)
    assert str(gone.resolve()) in removed
    assert store.read_entry(d["store_dir"], gone.resolve()) is None
    assert store.read_entry(d["store_dir"], alive.resolve()) is not None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_app.py -q`
Expected: FAIL — `AttributeError: module 'livery.app' has no attribute 'cmd_scan'`

- [ ] **Step 3: Voeg een delete-helper toe aan de store**

Append to `livery/store.py`:
```python
def delete_entry(store_dir, root):
    p = store_path(store_dir, root)
    if p.exists():
        p.unlink()
```

- [ ] **Step 4: Implementeer de commando's (toevoegen aan app.py)**

Append to `livery/app.py`:
```python
from livery.profile import profile_guid


def cmd_scan(cwd, profiles_dir, store_dir):
    root = find_project_root(cwd)
    theme = detect_theme()
    png = _autodetect(root)
    if png is None:
        return escapes.reset()
    rgb = color_from_png(png)
    if rgb is None:
        return escapes.reset()
    store.write_entry(store_dir, root, {
        "root": str(root), "icon_path": str(png),
        "dominant_color": list(rgb), "source": "manifest", "last_theme": theme,
    })
    _ensure_profile(profiles_dir, root, png, rgb, theme)
    return _emit_for(root, rgb, theme)


def cmd_set_icon(icon_path, cwd, profiles_dir, store_dir):
    root = find_project_root(cwd)
    theme = detect_theme()
    icon = Path(icon_path).expanduser().resolve()
    rgb = color_from_png(icon)
    if rgb is None:
        return escapes.reset()
    store.write_entry(store_dir, root, {
        "root": str(root), "icon_path": str(icon),
        "dominant_color": list(rgb), "source": "manual", "last_theme": theme,
    })
    _ensure_profile(profiles_dir, root, icon, rgb, theme)
    return _emit_for(root, rgb, theme)


def cmd_clean(profiles_dir, store_dir):
    removed = []
    for entry in list(store.iter_entries(store_dir)):
        root = entry.get("root", "")
        if root and not Path(root).exists():
            store.delete_entry(store_dir, root)
            pf = Path(profiles_dir) / f"{profile_guid(root)}.json"
            if pf.exists():
                pf.unlink()
            removed.append(root)
    return removed
```

- [ ] **Step 5: Run test to verify it passes**

Run: `python3 -m pytest tests/test_app.py -q`
Expected: PASS (7 passed)

- [ ] **Step 6: Commit**

```bash
git add livery/app.py livery/store.py tests/test_app.py
git commit -m "feat: scan, set-icon and clean commands"
```

---

## Task 13: CLI-dispatch (`__main__.py`)

**Files:**
- Create: `livery/__main__.py`
- Modify: `tests/test_app.py`

- [ ] **Step 1: Schrijf de falende test (subprocess-aanroep van het pakket)**

Append to `tests/test_app.py`:
```python
import subprocess
import sys
from pathlib import Path


def test_cli_emit_no_manifest_prints_reset(tmp_path, monkeypatch):
    repo = Path(__file__).resolve().parent.parent
    env = dict(**os.environ)
    proc = subprocess.run(
        [sys.executable, "-m", "livery", "emit",
         "--cwd", str(tmp_path),
         "--profiles-dir", str(tmp_path / "p"),
         "--store-dir", str(tmp_path / "s")],
        cwd=repo, env=env, capture_output=True, text=True,
    )
    assert proc.returncode == 0
    assert "SetProfile=Default" in proc.stdout
```
(Voeg bovenaan `tests/test_app.py` toe: `import os`.)

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_app.py::test_cli_emit_no_manifest_prints_reset -q`
Expected: FAIL — `No module named livery.__main__` / non-zero returncode

- [ ] **Step 3: Implementeer de dispatch**

Create `livery/__main__.py`:
```python
import argparse
import sys

from livery import app


def main(argv=None):
    parser = argparse.ArgumentParser(prog="livery")
    parser.add_argument("--cwd", default=".")
    parser.add_argument("--profiles-dir", default=str(app.DEFAULT_PROFILES))
    parser.add_argument("--store-dir", default=str(app.DEFAULT_STORE))
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("emit")
    sub.add_parser("scan")
    p_set = sub.add_parser("set-icon")
    p_set.add_argument("path")
    sub.add_parser("clean")

    a = parser.parse_args(argv)
    dirs = {"profiles_dir": a.profiles_dir, "store_dir": a.store_dir}

    if a.cmd == "emit":
        sys.stdout.write(app.cmd_emit(cwd=a.cwd, **dirs))
    elif a.cmd == "scan":
        sys.stdout.write(app.cmd_scan(cwd=a.cwd, **dirs))
    elif a.cmd == "set-icon":
        sys.stdout.write(app.cmd_set_icon(a.path, cwd=a.cwd, **dirs))
    elif a.cmd == "clean":
        for root in app.cmd_clean(**dirs):
            sys.stderr.write(f"removed {root}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_app.py -q`
Expected: PASS (8 passed)

- [ ] **Step 5: Commit**

```bash
git add livery/__main__.py tests/test_app.py
git commit -m "feat: argparse CLI dispatch"
```

---

## Task 14: zsh-laag

**Files:**
- Create: `livery.zsh`

- [ ] **Step 1: Schrijf de zsh-laag**

Create `livery.zsh`:
```zsh
# livery — source dit vanuit ~/.zshrc
LIVERY_DIR="${0:A:h}"

_livery_run() {
  [[ "$TERM_PROGRAM" == "iTerm.app" ]] || return 0
  local logfile="/dev/null"
  [[ -n "$LIVERY_LOG" ]] && logfile="$HOME/.config/livery/log"
  local out
  out="$(python3 "$LIVERY_DIR/livery" emit --cwd "$PWD" 2>>"$logfile")" || return 0
  print -rn -- "$out"
}

livery() {
  [[ "$TERM_PROGRAM" == "iTerm.app" ]] || { echo "livery: alleen in iTerm2"; return 1; }
  case "$1" in
    scan)   python3 "$LIVERY_DIR/livery" scan --cwd "$PWD" ;;
    set-icon) python3 "$LIVERY_DIR/livery" set-icon "$2" --cwd "$PWD" ;;
    clean)    python3 "$LIVERY_DIR/livery" clean ;;
    *) echo "usage: livery {scan|set-icon <pad>|clean}"; return 1 ;;
  esac
}

autoload -U add-zsh-hook
add-zsh-hook chpwd _livery_run
_livery_run   # bij startup
```

> Noot: `scan`/`set-icon` printen zelf de escape-sequences (ze retourneren die
> uit `app.py`), dus de tab update meteen. `clean` print niets naar de tab.

- [ ] **Step 2: Smoke-test de syntaxis**

Run: `zsh -n livery.zsh && echo OK`
Expected: `OK` (geen syntaxisfouten)

- [ ] **Step 3: Smoke-test sourcen + functie bestaat**

Run: `zsh -c 'source ./livery.zsh; type _livery_run >/dev/null && type livery >/dev/null && echo OK'`
Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add livery.zsh
git commit -m "feat: zsh hook layer with chpwd + livery command"
```

---

## Task 15: README + installatie

**Files:**
- Create: `README.md`

- [ ] **Step 1: Schrijf de README**

Create `README.md`:
```markdown
# livery

Geeft elke iTerm2-tab automatisch het icoon + de (gemute) merkkleur van het
project waarin je staat, op basis van `site.webmanifest`.

## Installatie

1. iTerm2 vereist: `brew install --cask iterm2`
2. Voeg aan `~/.zshrc` toe:
   ```sh
   source ~/projects/livery/livery.zsh
   ```
3. Open een nieuwe iTerm2-tab.

## Commando's

- `livery scan` — opnieuw afleiden uit `site.webmanifest`.
- `livery set-icon <pad>` — handmatig icoon-pad instellen (ook zonder manifest).
- `livery clean` — verweesde profielen/store-entries opruimen.

## Configuratie (env-vars)

| Var | Default | Effect |
|-----|---------|--------|
| `LIVERY_TAB_STRENGTH` | `0.15` | Blend-sterkte tab-kleur |
| `LIVERY_BG_STRENGTH` | `0.07` | Blend-sterkte terminal-achtergrond |
| `LIVERY_MAXDEPTH` | `6` | Max zoekdiepte vanaf project-root |
| `LIVERY_LOG` | (uit) | `1` = logregels naar `~/.config/livery/log` |

## Werking

Per project-root (omhoog tot `.git`) wordt één keer de favicon + dominante kleur
afgeleid en opgeslagen in `~/.config/livery/dirs/`. Daarna leest elke `cd`
puur die store. Een Dynamic Profile in iTerm2 draagt het icoon + de kleuren.
```

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "docs: README with install and usage"
```

---

## Task 16: Volledige testsuite + end-to-end in echte iTerm2

**Files:** geen (verificatie)

- [ ] **Step 1: Draai de volledige suite**

Run: `cd ~/projects/livery && python3 -m pytest -q`
Expected: alle tests PASS (sips-tests passen op macOS; anders skipped).

- [ ] **Step 2: Activeer in je echte shell**

Run: voeg de `source`-regel toe aan `~/.zshrc`, open een **nieuwe iTerm2-tab**.

- [ ] **Step 3: Test met een echt project**

Run in een project met een `site.webmanifest`:
```bash
cd ~/pad/naar/webproject
```
Expected: de tab krijgt het favicon-icoon + een subtiele tint; controleer
`ls ~/Library/Application\ Support/iTerm2/DynamicProfiles/` en
`ls ~/.config/livery/dirs/` (elk één bestand).

- [ ] **Step 4: Test reset + commando's**

Run:
```bash
cd /tmp                 # geen manifest -> terug naar Default-look
cd -                    # weer het project -> snelpad uit store
livery set-icon ~/pad/naar/eigen-logo.png   # handmatig icoon
livery scan                                # weer uit manifest
```
Expected: tab volgt elke keer; `set-icon` toont jouw logo; `scan` herstelt het manifest-icoon.

- [ ] **Step 5 (indien nodig): stem de sterktes af**

Vind je de tint te sterk/zwak: zet bijv. `export LIVERY_TAB_STRENGTH=0.10`
in `~/.zshrc`, open een nieuwe tab, `livery scan`.

- [ ] **Step 6: Commit eventuele bevindingen**

Als je tijdens E2E iets aanpaste (bv. default-sterktes), commit dat:
```bash
git add -A && git commit -m "chore: tune defaults after end-to-end check"
```

---

## Self-Review (uitgevoerd bij schrijven)

- **Spec-dekking:** iTerm2-guard (Taak 14), root-walk (2), recursief zoeken+prune+maxdepth (3), eerste PNG + padresolutie (4), dominant + average-fallback (5), sips-pipeline (6), thema + gemute tint tab/bg (7), per-root store als bron van waarheid (8), Dynamic Profile met icoon+kleuren (9), SetProfile+tabkleur+reset escapes (10), emit-snelpad (11), scan/set-icon/clean (12), CLI (13), zsh-hook+commando (14), README/config (15), E2E (16), sleutel-verificatie (0). Alle spec-secties gedekt.
- **Placeholders:** geen TBD/TODO; alle code-stappen bevatten volledige code.
- **Type-consistentie:** functienamen consistent over taken (`find_project_root`, `find_manifest`/`first_png`, `dominant_color`/`average_color`/`color_from_png`/`sips_pixels`, `detect_theme`/`mute`, `store_path`/`read_entry`/`write_entry`/`iter_entries`/`delete_entry`, `build_profile`/`write_profile`/`profile_file`/`profile_guid`/`profile_name`, `set_profile`/`tab_color`/`reset`, `cmd_emit`/`cmd_scan`/`cmd_set_icon`/`cmd_clean`/`_ensure_profile`/`_autodetect`/`_emit_for`). `app.detect_theme` en `app.color_from_png` zijn als module-attributen geïmporteerd zodat tests ze kunnen monkeypatchen.
```

---

# ADDENDUM: Tab-title feature (2026-06-12)

> Dit addendum **vervangt** de code/tests van Taken 10, 11, 12, 13, 14 en 16
> hierboven, en voegt **Taak 10b** (titel-module) toe. Bouw Taken 1–9 zoals
> hierboven; gebruik vanaf Taak 10 de versies in dit addendum.
>
> Wijzigingen: tab-titel via `OSC 0`; naam-bron manifest `name`→`short_name`→
> `.env`→mapnaam; `rename`-commando voor `"<name> | <custom>"`; env-only
> theming (titel zonder icoon); zsh draait de helper via `PYTHONPATH`/`-m`.

## Task 10 (REVISED): Escape-sequences (incl. titel + losse resets)

**Files:** Create `livery/escapes.py`, `tests/test_escapes.py`

- [ ] **Step 1: failing test** — Create `tests/test_escapes.py`:
```python
from livery.escapes import (
    default_look, reset, reset_tab_color, set_profile, tab_color, title,
)


def test_set_profile():
    assert set_profile("livery: x") == "\033]1337;SetProfile=livery: x\007"


def test_tab_color_three_channels():
    assert tab_color((10, 20, 30)) == ("\033]6;1;bg;red;brightness;10\007"
                                       "\033]6;1;bg;green;brightness;20\007"
                                       "\033]6;1;bg;blue;brightness;30\007")


def test_title():
    assert title("Slowboard | dev") == "\033]0;Slowboard | dev\007"


def test_reset_tab_color():
    assert reset_tab_color() == "\033]6;1;bg;*;default\007"


def test_default_look():
    assert default_look() == "\033]1337;SetProfile=Default\007\033]6;1;bg;*;default\007"


def test_reset_clears_title_then_default_look():
    assert reset() == "\033]0;\007\033]1337;SetProfile=Default\007\033]6;1;bg;*;default\007"
```

- [ ] **Step 2: verify fail** — `python3 -m pytest tests/test_escapes.py -q` → FAIL (No module named 'livery.escapes').

- [ ] **Step 3: implement** — Create `livery/escapes.py`:
```python
ESC = "\033"
BEL = "\007"


def set_profile(name):
    return f"{ESC}]1337;SetProfile={name}{BEL}"


def tab_color(rgb):
    r, g, b = rgb
    return (f"{ESC}]6;1;bg;red;brightness;{r}{BEL}"
            f"{ESC}]6;1;bg;green;brightness;{g}{BEL}"
            f"{ESC}]6;1;bg;blue;brightness;{b}{BEL}")


def reset_tab_color():
    return f"{ESC}]6;1;bg;*;default{BEL}"


def title(text):
    return f"{ESC}]0;{text}{BEL}"


def default_look():
    """Default-profiel + standaard tabkleur (titel onaangeroerd)."""
    return set_profile("Default") + reset_tab_color()


def reset():
    """Volledige reset voor een niet-themed map: titel wissen + default look."""
    return title("") + default_look()
```

- [ ] **Step 4: verify pass** — `python3 -m pytest tests/test_escapes.py -q` → PASS (6 passed).

- [ ] **Step 5: commit**
```bash
git add livery/escapes.py tests/test_escapes.py
git commit -m "feat: OSC escapes for profile, tab color and title"
```

## Task 10b (NEW): Titel-afleiding

**Files:** Create `livery/title.py`, `tests/test_title.py`

- [ ] **Step 1: failing test** — Create `tests/test_title.py`:
```python
from livery.title import base_name, name_from_env, name_from_manifest, tab_title


def test_name_from_manifest_prefers_name(tmp_path):
    m = tmp_path / "site.webmanifest"
    m.write_text('{"name":"Slowboard","short_name":"SB"}')
    assert name_from_manifest(m) == "Slowboard"


def test_name_from_manifest_falls_back_to_short_name(tmp_path):
    m = tmp_path / "site.webmanifest"
    m.write_text('{"short_name":"SB"}')
    assert name_from_manifest(m) == "SB"


def test_name_from_manifest_none_when_empty(tmp_path):
    m = tmp_path / "site.webmanifest"
    m.write_text("{}")
    assert name_from_manifest(m) is None


def test_name_from_env_first_nonempty_in_priority(tmp_path):
    (tmp_path / ".env").write_text('FOO=bar\nPROJECT_NAME="My App"\nNAME=ignored\n')
    assert name_from_env(tmp_path) == "My App"


def test_name_from_env_none_when_absent(tmp_path):
    assert name_from_env(tmp_path) is None


def test_base_name_precedence_manifest_over_env(tmp_path):
    m = tmp_path / "site.webmanifest"
    m.write_text('{"name":"FromManifest"}')
    (tmp_path / ".env").write_text("APP_NAME=FromEnv\n")
    assert base_name(tmp_path, m) == "FromManifest"


def test_base_name_uses_env_without_manifest(tmp_path):
    (tmp_path / ".env").write_text("APP_NAME=FromEnv\n")
    assert base_name(tmp_path, None) == "FromEnv"


def test_base_name_falls_back_to_dirname(tmp_path):
    d = tmp_path / "slowboard"
    d.mkdir()
    assert base_name(d, None) == "slowboard"


def test_tab_title_with_and_without_custom():
    assert tab_title("Slowboard", "dev") == "Slowboard | dev"
    assert tab_title("Slowboard", None) == "Slowboard"
    assert tab_title("Slowboard", "") == "Slowboard"
```

- [ ] **Step 2: verify fail** — `python3 -m pytest tests/test_title.py -q` → FAIL (No module named 'livery.title').

- [ ] **Step 3: implement** — Create `livery/title.py`:
```python
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
```

- [ ] **Step 4: verify pass** — `python3 -m pytest tests/test_title.py -q` → PASS (9 passed).

- [ ] **Step 5: commit**
```bash
git add livery/title.py tests/test_title.py
git commit -m "feat: tab title name derivation (manifest -> .env -> dirname)"
```

## Task 11 (REVISED): Orchestratie — `emit` (titel + env-only theming)

**Files:** Create `livery/app.py`, `tests/test_app.py`

- [ ] **Step 1: failing test** — Create `tests/test_app.py`:
```python
import os

from livery import app, escapes, store
from livery.profile import profile_file


def _dirs(tmp_path):
    return {"profiles_dir": tmp_path / "profiles", "store_dir": tmp_path / "store"}


def test_emit_not_a_project_returns_reset(tmp_path, monkeypatch):
    monkeypatch.setattr(app, "detect_theme", lambda: "dark")
    out = app.cmd_emit(cwd=tmp_path, **_dirs(tmp_path))
    assert out == escapes.reset()


def test_emit_manifest_sets_icon_color_and_title(tmp_path, make_png, monkeypatch):
    monkeypatch.setattr(app, "detect_theme", lambda: "dark")
    monkeypatch.setattr(app, "color_from_png", lambda p: (40, 80, 200))
    (tmp_path / "site.webmanifest").write_text('{"name":"Slowboard","icons":[{"src":"a.png"}]}')
    make_png(tmp_path / "a.png", (40, 80, 200))
    d = _dirs(tmp_path)

    out = app.cmd_emit(cwd=tmp_path, **d)

    assert "]0;Slowboard\007" in out
    assert "SetProfile=livery:" in out
    entry = store.read_entry(d["store_dir"], tmp_path.resolve())
    assert entry["dominant_color"] == [40, 80, 200]
    assert entry["name"] == "Slowboard"
    assert entry["source"] == "manifest"
    assert profile_file(d["profiles_dir"], tmp_path.resolve()).exists()


def test_emit_env_only_sets_title_no_icon(tmp_path, monkeypatch):
    monkeypatch.setattr(app, "detect_theme", lambda: "dark")
    (tmp_path / ".env").write_text("APP_NAME=EnvApp\n")
    d = _dirs(tmp_path)

    out = app.cmd_emit(cwd=tmp_path, **d)

    assert "]0;EnvApp\007" in out
    assert "SetProfile=Default" in out
    entry = store.read_entry(d["store_dir"], tmp_path.resolve())
    assert entry["icon_path"] is None
    assert entry["name"] == "EnvApp"
    assert entry["source"] == "env"


def test_emit_uses_store_without_rescanning(tmp_path, make_png, monkeypatch):
    monkeypatch.setattr(app, "detect_theme", lambda: "dark")
    d = _dirs(tmp_path)
    icon = tmp_path / "a.png"
    make_png(icon, (40, 80, 200))
    store.write_entry(d["store_dir"], tmp_path.resolve(), {
        "root": str(tmp_path.resolve()), "icon_path": str(icon),
        "dominant_color": [40, 80, 200], "name": "Cached", "custom_name": None,
        "source": "manifest", "last_theme": "dark",
    })

    def boom(_):
        raise AssertionError("color_from_png mag niet draaien op het snelpad")

    monkeypatch.setattr(app, "color_from_png", boom)
    out = app.cmd_emit(cwd=tmp_path, **d)
    assert "]0;Cached\007" in out
    assert "SetProfile=livery:" in out


def test_emit_missing_icon_file_resets(tmp_path, monkeypatch):
    monkeypatch.setattr(app, "detect_theme", lambda: "dark")
    d = _dirs(tmp_path)
    store.write_entry(d["store_dir"], tmp_path.resolve(), {
        "root": str(tmp_path.resolve()), "icon_path": str(tmp_path / "gone.png"),
        "dominant_color": [1, 2, 3], "name": "X", "custom_name": None,
        "source": "manifest", "last_theme": "dark",
    })
    out = app.cmd_emit(cwd=tmp_path, **d)
    assert out == escapes.reset()
```

- [ ] **Step 2: verify fail** — `python3 -m pytest tests/test_app.py -q` → FAIL (No module named 'livery.app').

- [ ] **Step 3: implement** — Create `livery/app.py`:
```python
import os
from pathlib import Path

from livery import escapes, store
from livery.color import color_from_png
from livery.manifest import find_manifest, first_png
from livery.profile import build_profile, profile_file, profile_name, write_profile
from livery.roots import find_project_root
from livery.tint import detect_theme, mute
from livery.title import base_name, tab_title

DEFAULT_STORE = Path.home() / ".config" / "livery" / "dirs"
DEFAULT_PROFILES = Path.home() / "Library" / "Application Support" / "iTerm2" / "DynamicProfiles"


def _tab_strength():
    return float(os.environ.get("LIVERY_TAB_STRENGTH", "0.15"))


def _bg_strength():
    return float(os.environ.get("LIVERY_BG_STRENGTH", "0.07"))


def _maxdepth():
    return int(os.environ.get("LIVERY_MAXDEPTH", "6"))


def _detect(root, force=False):
    """Bouw store-velden voor een root. None als 't geen project is (en niet force)."""
    manifest = find_manifest(root, maxdepth=_maxdepth())
    has_env = (Path(root) / ".env").exists()
    if manifest is None and not has_env and not force:
        return None
    png = first_png(manifest) if manifest else None
    if png is not None and not Path(png).exists():
        png = None
    rgb = color_from_png(png) if png else None
    source = "manifest" if png else ("env" if has_env else "name")
    return {
        "root": str(root),
        "icon_path": str(png) if png else None,
        "dominant_color": list(rgb) if rgb else None,
        "name": base_name(root, manifest),
        "custom_name": None,
        "source": source,
        "last_theme": None,
    }


def _ensure_profile(profiles_dir, entry, theme):
    """Schrijf het Dynamic Profile, maar alleen als de entry een icoon heeft."""
    if not entry.get("icon_path") or not entry.get("dominant_color"):
        return
    rgb = tuple(entry["dominant_color"])
    tab = mute(rgb, theme, _tab_strength())
    bg = mute(rgb, theme, _bg_strength())
    write_profile(profiles_dir, build_profile(entry["root"], entry["icon_path"], tab, bg))


def _emit(entry, theme):
    """Escape-output: titel + (icoon-profiel + kleur) OF default-look."""
    out = escapes.title(tab_title(entry["name"], entry.get("custom_name")))
    if entry.get("icon_path") and entry.get("dominant_color"):
        rgb = tuple(entry["dominant_color"])
        out += escapes.set_profile(profile_name(entry["root"]))
        out += escapes.tab_color(mute(rgb, theme, _tab_strength()))
    else:
        out += escapes.default_look()
    return out


def cmd_emit(cwd, profiles_dir, store_dir):
    root = find_project_root(cwd)
    theme = detect_theme()
    entry = store.read_entry(store_dir, root)

    if entry is None:
        entry = _detect(root)
        if entry is None:
            return escapes.reset()
        entry["last_theme"] = theme
        store.write_entry(store_dir, root, entry)
        _ensure_profile(profiles_dir, entry, theme)
        return _emit(entry, theme)

    if entry.get("icon_path") and not Path(entry["icon_path"]).exists():
        return escapes.reset()

    needs_profile = entry.get("icon_path") and not profile_file(profiles_dir, root).exists()
    if entry.get("last_theme") != theme or needs_profile:
        _ensure_profile(profiles_dir, entry, theme)
        entry["last_theme"] = theme
        store.write_entry(store_dir, root, entry)
    return _emit(entry, theme)
```

- [ ] **Step 4: verify pass** — `python3 -m pytest tests/test_app.py -q` → PASS (5 passed).

- [ ] **Step 5: commit**
```bash
git add livery/app.py tests/test_app.py
git commit -m "feat: emit orchestration with title + env-only theming"
```

## Task 12 (REVISED): `scan`, `set-icon`, `rename`, `clean`

**Files:** Modify `livery/app.py`, `livery/store.py`, `tests/test_app.py`

- [ ] **Step 1: failing test** — APPEND to `tests/test_app.py`:
```python
def test_scan_overwrites_entry_keeps_custom(tmp_path, make_png, monkeypatch):
    monkeypatch.setattr(app, "detect_theme", lambda: "dark")
    d = _dirs(tmp_path)
    (tmp_path / "site.webmanifest").write_text('{"name":"Slow","icons":[{"src":"a.png"}]}')
    make_png(tmp_path / "a.png", (10, 10, 200))
    store.write_entry(d["store_dir"], tmp_path.resolve(), {
        "root": str(tmp_path.resolve()), "icon_path": "/old.png",
        "dominant_color": [1, 1, 1], "name": "Old", "custom_name": "dev",
        "source": "manifest", "last_theme": "dark",
    })
    monkeypatch.setattr(app, "color_from_png", lambda p: (10, 10, 200))
    app.cmd_scan(cwd=tmp_path, **d)
    entry = store.read_entry(d["store_dir"], tmp_path.resolve())
    assert entry["dominant_color"] == [10, 10, 200]
    assert entry["icon_path"].endswith("a.png")
    assert entry["name"] == "Slow"
    assert entry["custom_name"] == "dev"


def test_set_icon_sets_manual_source_and_dirname(tmp_path, make_png, monkeypatch):
    monkeypatch.setattr(app, "detect_theme", lambda: "dark")
    d = _dirs(tmp_path)
    icon = tmp_path / "logo.png"
    make_png(icon, (200, 10, 10))
    monkeypatch.setattr(app, "color_from_png", lambda p: (200, 10, 10))
    app.cmd_set_icon(str(icon), cwd=tmp_path, **d)
    entry = store.read_entry(d["store_dir"], tmp_path.resolve())
    assert entry["source"] == "manual"
    assert entry["icon_path"] == str(icon)
    assert entry["dominant_color"] == [200, 10, 10]
    assert entry["name"] == tmp_path.name


def test_rename_sets_and_clears_custom(tmp_path, monkeypatch):
    monkeypatch.setattr(app, "detect_theme", lambda: "dark")
    d = _dirs(tmp_path)
    (tmp_path / ".env").write_text("APP_NAME=EnvApp\n")
    out = app.cmd_rename("dev", cwd=tmp_path, **d)
    assert "]0;EnvApp | dev\007" in out
    assert store.read_entry(d["store_dir"], tmp_path.resolve())["custom_name"] == "dev"
    app.cmd_rename("", cwd=tmp_path, **d)
    assert store.read_entry(d["store_dir"], tmp_path.resolve())["custom_name"] is None


def test_rename_on_bare_dir_uses_dirname(tmp_path, monkeypatch):
    monkeypatch.setattr(app, "detect_theme", lambda: "dark")
    d = _dirs(tmp_path)
    out = app.cmd_rename("x", cwd=tmp_path, **d)
    assert f"]0;{tmp_path.name} | x\007" in out


def test_clean_removes_orphan_entries(tmp_path):
    d = _dirs(tmp_path)
    gone = tmp_path / "gone"
    alive = tmp_path / "alive"
    alive.mkdir()
    for root in (gone, alive):
        entry = {"root": str(root.resolve()), "icon_path": "x.png",
                 "dominant_color": [1, 2, 3], "name": "n", "custom_name": None,
                 "source": "manifest", "last_theme": "dark"}
        store.write_entry(d["store_dir"], root.resolve(), entry)
        app._ensure_profile(d["profiles_dir"], entry, "dark")
    removed = app.cmd_clean(**d)
    assert str(gone.resolve()) in removed
    assert store.read_entry(d["store_dir"], gone.resolve()) is None
    assert store.read_entry(d["store_dir"], alive.resolve()) is not None
```

- [ ] **Step 2: verify fail** — `python3 -m pytest tests/test_app.py -q` → FAIL (AttributeError: module 'livery.app' has no attribute 'cmd_scan').

- [ ] **Step 3: store delete helper** — APPEND to `livery/store.py`:
```python
def delete_entry(store_dir, root):
    p = store_path(store_dir, root)
    if p.exists():
        p.unlink()
```

- [ ] **Step 4: implement** — APPEND to `livery/app.py`:
```python
from livery.profile import profile_guid


def cmd_scan(cwd, profiles_dir, store_dir):
    root = find_project_root(cwd)
    theme = detect_theme()
    old = store.read_entry(store_dir, root)
    entry = _detect(root)
    if entry is None:
        return escapes.reset()
    if old and old.get("custom_name"):
        entry["custom_name"] = old["custom_name"]
    entry["last_theme"] = theme
    store.write_entry(store_dir, root, entry)
    _ensure_profile(profiles_dir, entry, theme)
    return _emit(entry, theme)


def cmd_set_icon(icon_path, cwd, profiles_dir, store_dir):
    root = find_project_root(cwd)
    theme = detect_theme()
    icon = Path(icon_path).expanduser().resolve()
    rgb = color_from_png(icon)
    if rgb is None:
        return escapes.reset()
    old = store.read_entry(store_dir, root)
    name = old["name"] if old and old.get("name") else base_name(root, find_manifest(root, maxdepth=_maxdepth()))
    entry = {
        "root": str(root), "icon_path": str(icon), "dominant_color": list(rgb),
        "name": name, "custom_name": old.get("custom_name") if old else None,
        "source": "manual", "last_theme": theme,
    }
    store.write_entry(store_dir, root, entry)
    _ensure_profile(profiles_dir, entry, theme)
    return _emit(entry, theme)


def cmd_rename(custom, cwd, profiles_dir, store_dir):
    root = find_project_root(cwd)
    theme = detect_theme()
    entry = store.read_entry(store_dir, root) or _detect(root, force=True)
    entry["custom_name"] = custom or None
    entry["last_theme"] = theme
    store.write_entry(store_dir, root, entry)
    _ensure_profile(profiles_dir, entry, theme)
    return _emit(entry, theme)


def cmd_clean(profiles_dir, store_dir):
    removed = []
    for entry in list(store.iter_entries(store_dir)):
        root = entry.get("root", "")
        if root and not Path(root).exists():
            store.delete_entry(store_dir, root)
            pf = Path(profiles_dir) / f"{profile_guid(root)}.json"
            if pf.exists():
                pf.unlink()
            removed.append(root)
    return removed
```

- [ ] **Step 5: verify pass** — `python3 -m pytest tests/test_app.py -q` → PASS (10 passed).

- [ ] **Step 6: commit**
```bash
git add livery/app.py livery/store.py tests/test_app.py
git commit -m "feat: scan, set-icon, rename and clean commands"
```

## Task 13 (REVISED): CLI-dispatch (incl. `rename`)

**Files:** Create `livery/__main__.py`, modify `tests/test_app.py`

- [ ] **Step 1: failing test** — APPEND to `tests/test_app.py`:
```python
import subprocess
import sys
from pathlib import Path


def test_cli_emit_not_a_project_prints_reset(tmp_path):
    repo = Path(__file__).resolve().parent.parent
    proc = subprocess.run(
        [sys.executable, "-m", "livery", "emit",
         "--cwd", str(tmp_path),
         "--profiles-dir", str(tmp_path / "p"),
         "--store-dir", str(tmp_path / "s")],
        cwd=repo, env=dict(os.environ), capture_output=True, text=True,
    )
    assert proc.returncode == 0
    assert "SetProfile=Default" in proc.stdout


def test_cli_rename_prints_title(tmp_path):
    repo = Path(__file__).resolve().parent.parent
    (tmp_path / ".env").write_text("APP_NAME=EnvApp\n")
    proc = subprocess.run(
        [sys.executable, "-m", "livery", "rename", "dev",
         "--cwd", str(tmp_path),
         "--profiles-dir", str(tmp_path / "p"),
         "--store-dir", str(tmp_path / "s")],
        cwd=repo, env=dict(os.environ), capture_output=True, text=True,
    )
    assert proc.returncode == 0
    assert "]0;EnvApp | dev\007" in proc.stdout
```

- [ ] **Step 2: verify fail** — `python3 -m pytest tests/test_app.py -k cli -q` → FAIL (No module named livery.__main__ / non-zero returncode).

- [ ] **Step 3: implement** — Create `livery/__main__.py`:
```python
import argparse
import sys

from livery import app


def main(argv=None):
    parser = argparse.ArgumentParser(prog="livery")
    parser.add_argument("--cwd", default=".")
    parser.add_argument("--profiles-dir", default=str(app.DEFAULT_PROFILES))
    parser.add_argument("--store-dir", default=str(app.DEFAULT_STORE))
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("emit")
    sub.add_parser("scan")
    p_set = sub.add_parser("set-icon")
    p_set.add_argument("path")
    p_ren = sub.add_parser("rename")
    p_ren.add_argument("custom", nargs="?", default="")
    sub.add_parser("clean")

    a = parser.parse_args(argv)
    dirs = {"profiles_dir": a.profiles_dir, "store_dir": a.store_dir}

    if a.cmd == "emit":
        sys.stdout.write(app.cmd_emit(cwd=a.cwd, **dirs))
    elif a.cmd == "scan":
        sys.stdout.write(app.cmd_scan(cwd=a.cwd, **dirs))
    elif a.cmd == "set-icon":
        sys.stdout.write(app.cmd_set_icon(a.path, cwd=a.cwd, **dirs))
    elif a.cmd == "rename":
        sys.stdout.write(app.cmd_rename(a.custom, cwd=a.cwd, **dirs))
    elif a.cmd == "clean":
        for root in app.cmd_clean(**dirs):
            sys.stderr.write(f"removed {root}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: verify pass** — `python3 -m pytest tests/test_app.py -q` → PASS (12 passed).

- [ ] **Step 5: commit**
```bash
git add livery/__main__.py tests/test_app.py
git commit -m "feat: argparse CLI dispatch with rename"
```

## Task 14 (REVISED): zsh-laag (PYTHONPATH/-m + rename)

**Files:** Create `livery.zsh`

- [ ] **Step 1: implement** — Create `livery.zsh`:
```zsh
# livery — source dit vanuit ~/.zshrc
LIVERY_DIR="${0:A:h}"

_livery_py() {
  # Draai het pakket met de repo-root op PYTHONPATH zodat `import livery` werkt.
  PYTHONPATH="$LIVERY_DIR" python3 -m livery "$@"
}

_livery_run() {
  [[ "$TERM_PROGRAM" == "iTerm.app" ]] || return 0
  local logfile="/dev/null"
  [[ -n "$LIVERY_LOG" ]] && logfile="$HOME/.config/livery/log"
  local out
  out="$(_livery_py emit --cwd "$PWD" 2>>"$logfile")" || return 0
  print -rn -- "$out"
}

livery() {
  [[ "$TERM_PROGRAM" == "iTerm.app" ]] || { echo "livery: alleen in iTerm2"; return 1; }
  local out
  case "$1" in
    scan)   out="$(_livery_py scan --cwd "$PWD")" ;;
    set-icon) out="$(_livery_py set-icon "$2" --cwd "$PWD")" ;;
    rename)   out="$(_livery_py rename "$2" --cwd "$PWD")" ;;
    clean)    _livery_py clean; return 0 ;;
    *) echo "usage: livery {scan|set-icon <pad>|rename [naam]|clean}"; return 1 ;;
  esac
  print -rn -- "$out"
}

autoload -U add-zsh-hook
add-zsh-hook chpwd _livery_run
_livery_run   # bij startup
```

> `scan`/`set-icon`/`rename` retourneren de escape-sequences uit `app.py`, dus
> de tab werkt meteen bij. `clean` print alleen status (stderr) en raakt de tab niet.

- [ ] **Step 2: smoke-test syntaxis** — `zsh -n livery.zsh && echo OK` → `OK`.

- [ ] **Step 3: smoke-test sourcen** — `zsh -c 'source ./livery.zsh; type _livery_run >/dev/null && type livery >/dev/null && echo OK'` → `OK`.

- [ ] **Step 4: commit**
```bash
git add livery.zsh
git commit -m "feat: zsh hook layer with chpwd + livery command (incl rename)"
```

## Task 16 (REVISED): Suite + end-to-end (incl. titel)

- [ ] **Step 1: volledige suite** — `cd ~/projects/livery && python3 -m pytest -q` → alle PASS.
- [ ] **Step 2: activeren** — voeg `source ~/projects/livery/livery.zsh` toe aan `~/.zshrc`, open een **nieuwe iTerm2-tab**.
- [ ] **Step 3: manifest-project** — `cd` naar een webproject met `site.webmanifest`: tab krijgt icoon + tint + titel (manifest-naam). Check `~/.config/livery/dirs/` en de DynamicProfiles-map.
- [ ] **Step 4: env-only + titel-persistentie** — `cd` naar een map met alleen `.env` (met `APP_NAME`): tab krijgt de titel maar geen custom icoon. **Belangrijk:** controleer of de titel blijft staan na een paar prompts; als je zsh-config de titel in `precmd` herschrijft, los dat op (bv. de hook ná je titel-setter laten draaien, of de titel-setter uitschakelen).
- [ ] **Step 5: rename + reset** — `livery rename dev` → titel wordt `<Naam> | dev`; `livery rename` (leeg) → suffix weg; `cd /tmp` (geen manifest/env) → reset.
- [ ] **Step 6: sterktes afstemmen** (optioneel) — `export LIVERY_TAB_STRENGTH=0.10` etc., nieuwe tab, `livery scan`.
- [ ] **Step 7: commit eventuele tuning.**
