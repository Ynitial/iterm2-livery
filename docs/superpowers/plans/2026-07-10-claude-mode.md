# Claude-modus Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Een `claude`-shellwrapper die de iTerm2-tab per-invocation een Claude-oranje "AI-look" (achtergrond, leesbaar palet, 🦀-titel) geeft en bij afsluiten terugvalt op de normale livery-look, plus een Claude Code custom-thema voor leesbare tekst binnen claude.

**Architecture:** Twee gescheiden delen. **Deel A** (per-invocation, iTerm2): een gedeeld dynamisch profiel per commando met oranje achtergrond + afgestemd ANSI-palet; de zsh-wrapper schakelt ernaartoe + zet de 🦀-titel bij start en her-emit de normale look bij afsluiten. **Deel B** (eenmalige setup): een `~/.claude/themes/livery-claude.json` + activatie in `~/.claude/settings.json`. Config van te wrappen commando's leeft in `~/.config/livery/commands.json`, gelezen door zowel Python (emit) als zsh (wrapper-generatie).

**Tech Stack:** Python 3 (stdlib only), zsh, iTerm2 Dynamic Profiles + escape codes, pytest.

## Global Constraints

- **Alleen stdlib** — geen externe Python-dependencies (net als de rest van livery).
- **Alleen iTerm2** — buiten iTerm2 draaien wrappers het echte commando ongewijzigd.
- **Claude-oranje = `rgb(217, 119, 87)` = `#D97757`** (verbatim).
- **Per-invocation, nooit in een projectprofiel** — de oranje look is een tijdelijke overlay.
- **DRY/YAGNI/TDD**, frequente commits, exacte paden.
- Tests volgen de bestaande stijl in `tests/`: `pytest`, `tmp_path`, de `make_png`-fixture uit `tests/conftest.py`, en waar nuttig `monkeypatch`.
- Draai tests met `python3 -m pytest`.

---

## Bestandsoverzicht

- **Nieuw** `livery/palette.py` — het oranje-achtergrond ANSI-palet + `contrast_ratio`.
- **Nieuw** `livery/commands.py` — lezer/defaults voor `commands.json`.
- **Nieuw** `livery/claude_theme.py` — Claude Code themabestand + `settings.json`-activatie.
- **Gewijzigd** `livery/profile.py` — builder voor het per-commando profiel.
- **Gewijzigd** `livery/app.py` — `_emit`-refactor + `cmd_command_start`, `cmd_commands`, `cmd_claude_setup`.
- **Gewijzigd** `livery/__main__.py` — subcommando's `command-start`, `commands`, `claude-setup`.
- **Gewijzigd** `livery.zsh` — wrapper-generatie uit `commands.json`.
- **Gewijzigd** `README.md` — korte sectie Claude-modus.
- **Nieuw** tests: `tests/test_palette.py`, `tests/test_commands.py`, `tests/test_claude_theme.py`, uitbreidingen in `tests/test_profile.py` en `tests/test_app.py`.

---

### Task 1: ANSI-palet + contrastfunctie

**Files:**
- Create: `livery/palette.py`
- Test: `tests/test_palette.py`

**Interfaces:**
- Produces:
  - `BG = "#D97757"` (str hex)
  - `FOREGROUND = "#2B1810"` (str hex)
  - `ANSI = [<16 hex strings>]` (list[str], index 0..15)
  - `contrast_ratio(hex_a: str, hex_b: str) -> float`

- [ ] **Step 1: Schrijf de falende test**

```python
# tests/test_palette.py
from livery import palette


def test_foreground_is_high_contrast_on_orange():
    # De default-tekstkleur moet ruim leesbaar zijn op het oranje (WCAG AA).
    assert palette.contrast_ratio(palette.FOREGROUND, palette.BG) >= 4.5


def test_all_ansi_colors_stay_legible_on_orange():
    # Elke accentkleur moet minstens een legibiliteits-vloer halen op oranje.
    assert len(palette.ANSI) == 16
    for hexcol in palette.ANSI:
        assert palette.contrast_ratio(hexcol, palette.BG) >= 1.8, hexcol


def test_contrast_ratio_symmetric_and_white_on_black_is_21():
    assert round(palette.contrast_ratio("#FFFFFF", "#000000"), 1) == 21.0
    assert palette.contrast_ratio("#FFFFFF", "#000000") == palette.contrast_ratio("#000000", "#FFFFFF")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_palette.py -v`
Expected: FAIL met `ModuleNotFoundError: No module named 'livery.palette'`

- [ ] **Step 3: Schrijf de implementatie**

```python
# livery/palette.py
"""Kleuren voor de Claude-modus: een oranje achtergrond met een donker,
leesbaar ANSI-palet (donkere tekst op oranje = een 'light'-achtige look)."""

BG = "#D97757"          # Claude-oranje, rgb(217,119,87)
FOREGROUND = "#2B1810"  # donkerbruin; contrast ~5.4 op het oranje

# 16 ANSI-kleuren, bewust donker/verzadigd zodat álle tekst leesbaar blijft op
# het oranje; onderscheid zit in de tint, niet in de helderheid.
ANSI = [
    "#211A16",  # 0  zwart
    "#7A1F12",  # 1  rood
    "#2F5A22",  # 2  groen
    "#6B4A12",  # 3  geel
    "#243D66",  # 4  blauw
    "#5C2450",  # 5  magenta
    "#1E534F",  # 6  cyaan
    "#3A2E26",  # 7  'wit' (donker gehouden voor leesbaarheid)
    "#3A302A",  # 8  fel zwart
    "#8E2E1C",  # 9  fel rood
    "#356423",  # 10 fel groen
    "#6E4E18",  # 11 fel geel
    "#2E4C7E",  # 12 fel blauw
    "#6E2E60",  # 13 fel magenta
    "#286460",  # 14 fel cyaan
    "#4A3C30",  # 15 fel wit (donker gehouden)
]


def _rgb(hexcol):
    h = hexcol.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def _luminance(hexcol):
    def chan(c):
        c /= 255
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (chan(c) for c in _rgb(hexcol))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast_ratio(hex_a, hex_b):
    """WCAG-contrastverhouding (1.0–21.0) tussen twee hex-kleuren."""
    la, lb = _luminance(hex_a), _luminance(hex_b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_palette.py -v`
Expected: PASS (3 tests). Faalt een ANSI-kleur op de 1.8-vloer, maak 'm donkerder (verlaag de kanaalwaarden) tot 'ie slaagt.

- [ ] **Step 5: Commit**

```bash
git add livery/palette.py tests/test_palette.py
git commit -m "feat: oranje ANSI-palet + contrast-helper voor Claude-modus"
```

---

### Task 2: Per-commando profiel-builder

**Files:**
- Modify: `livery/profile.py`
- Test: `tests/test_profile.py`

**Interfaces:**
- Consumes: `livery.palette.BG`, `livery.palette.FOREGROUND`, `livery.palette.ANSI`; bestaande `write_profile(profiles_dir, profile)`.
- Produces:
  - `command_profile_guid(name: str) -> str`  (bv. `"livery-cmd-" + sha1(name)[:16]`)
  - `command_profile_name(name: str) -> str`  (bv. `f"livery:{name}"`)
  - `build_command_profile(name: str, bg_hex: str) -> dict`
  - `command_profile_file(profiles_dir, name) -> Path`

- [ ] **Step 1: Schrijf de falende test**

```python
# tests/test_profile.py  (voeg toe onderaan)
from livery import palette
from livery.profile import (
    build_command_profile, command_profile_name, command_profile_guid,
)


def test_build_command_profile_forces_orange_regardless_of_theme():
    p = build_command_profile("claude", palette.BG)
    assert p["Name"] == command_profile_name("claude") == "livery:claude"
    assert p["Guid"] == command_profile_guid("claude")
    # Dwing één achtergrond af, ongeacht dark/light.
    assert p["Use Separate Colors for Light and Dark Mode"] is False
    bg = p["Background Color"]
    assert round(bg["Red Component"] * 255) == 217
    assert round(bg["Green Component"] * 255) == 119
    assert round(bg["Blue Component"] * 255) == 87
    # Volledig 16-kleuren ANSI-palet aanwezig.
    for i in range(16):
        assert f"Ansi {i} Color" in p
    assert p["Dynamic Profile Parent Name"] == "Default"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_profile.py -v -k command_profile`
Expected: FAIL met `ImportError` / `cannot import name 'build_command_profile'`

- [ ] **Step 3: Schrijf de implementatie**

```python
# livery/profile.py  (voeg toe; hergebruik bestaande _color en hashlib/Path imports)
from livery import palette


def command_profile_guid(name):
    return "livery-cmd-" + hashlib.sha1(name.encode()).hexdigest()[:16]


def command_profile_name(name):
    return f"livery:{name}"


def command_profile_file(profiles_dir, name):
    return Path(profiles_dir) / f"{command_profile_guid(name)}.json"


def _color_hex(hexcol):
    h = hexcol.lstrip("#")
    return _color(tuple(int(h[i:i + 2], 16) for i in (0, 2, 4)))


def build_command_profile(name, bg_hex):
    """Profiel voor de commando-look: één afgedwongen achtergrond + donker palet.

    Bewust GEEN 'Use Separate Colors ...': we willen oranje in dark én light."""
    profile = {
        "Name": command_profile_name(name),
        "Guid": command_profile_guid(name),
        "Dynamic Profile Parent Name": "Default",
        "Use Separate Colors for Light and Dark Mode": False,
        "Background Color": _color_hex(bg_hex),
        "Foreground Color": _color_hex(palette.FOREGROUND),
    }
    for i, hexcol in enumerate(palette.ANSI):
        profile[f"Ansi {i} Color"] = _color_hex(hexcol)
    return profile
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_profile.py -v`
Expected: PASS (bestaande + nieuwe tests).

- [ ] **Step 5: Commit**

```bash
git add livery/profile.py tests/test_profile.py
git commit -m "feat: build_command_profile — afgedwongen oranje profiel + palet"
```

---

### Task 3: commands.json-lezer

**Files:**
- Create: `livery/commands.py`
- Test: `tests/test_commands.py`

**Interfaces:**
- Produces:
  - `DEFAULT_COMMANDS: dict` — bevat minstens `"claude": {"emoji": "🦀", "bg": [217,119,87], "fullscreen": True}`
  - `load(path) -> dict` — leest JSON; valt terug op `DEFAULT_COMMANDS` bij ontbreken/fout.
  - `ensure(path) -> dict` — schrijft `DEFAULT_COMMANDS` als het bestand ontbreekt; geeft de (nu bestaande) config terug.

- [ ] **Step 1: Schrijf de falende test**

```python
# tests/test_commands.py
import json

from livery import commands


def test_load_missing_returns_defaults(tmp_path):
    cfg = commands.load(tmp_path / "nope.json")
    assert cfg["claude"]["emoji"] == "🦀"
    assert cfg["claude"]["bg"] == [217, 119, 87]
    assert cfg["claude"]["fullscreen"] is True


def test_load_invalid_json_returns_defaults(tmp_path):
    p = tmp_path / "commands.json"
    p.write_text("{not json")
    assert commands.load(p)["claude"]["emoji"] == "🦀"


def test_load_reads_user_config(tmp_path):
    p = tmp_path / "commands.json"
    p.write_text(json.dumps({"codex": {"emoji": "🤖", "bg": [10, 20, 30], "fullscreen": False}}))
    cfg = commands.load(p)
    assert "codex" in cfg and cfg["codex"]["emoji"] == "🤖"


def test_ensure_writes_defaults_when_missing(tmp_path):
    p = tmp_path / "sub" / "commands.json"
    cfg = commands.ensure(p)
    assert p.exists()
    assert json.loads(p.read_text())["claude"]["emoji"] == "🦀"
    assert cfg["claude"]["fullscreen"] is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_commands.py -v`
Expected: FAIL met `ModuleNotFoundError: No module named 'livery.commands'`

- [ ] **Step 3: Schrijf de implementatie**

```python
# livery/commands.py
"""Per-commando config voor de wrappers. Eén bron van waarheid, gelezen door
zowel Python (emit) als zsh (wrapper-generatie via `livery commands`)."""
import json
from pathlib import Path

DEFAULT_COMMANDS = {
    "claude": {"emoji": "🦀", "bg": [217, 119, 87], "fullscreen": True},
}


def load(path):
    p = Path(path)
    if not p.exists():
        return dict(DEFAULT_COMMANDS)
    try:
        data = json.loads(p.read_text())
    except (OSError, ValueError):
        return dict(DEFAULT_COMMANDS)
    return data if isinstance(data, dict) else dict(DEFAULT_COMMANDS)


def ensure(path):
    p = Path(path)
    if not p.exists():
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(DEFAULT_COMMANDS, indent=2, ensure_ascii=False))
    return load(p)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_commands.py -v`
Expected: PASS (4 tests).

- [ ] **Step 5: Commit**

```bash
git add livery/commands.py tests/test_commands.py
git commit -m "feat: commands.json-lezer met defaults (claude → 🦀)"
```

---

### Task 4: Claude Code thema + settings-activatie

**Files:**
- Create: `livery/claude_theme.py`
- Test: `tests/test_claude_theme.py`

**Interfaces:**
- Consumes: `livery.palette` (voor tekst-/oranje-tinten).
- Produces:
  - `SLUG = "livery-claude"`
  - `theme_json() -> dict` — `{"name","base","overrides"}`
  - `write_theme(themes_dir) -> Path` — schrijft `<themes_dir>/livery-claude.json`
  - `activate(settings_path) -> None` — merget `"theme": "custom:livery-claude"` in settings.json (behoudt overige sleutels)

> **Bouw-notitie:** de exacte token-namen komen uit docs-research en moeten in
> Task 8 tegen de draaiende Claude Code-versie geverifieerd worden (`/theme`).
> Onbekende tokens worden door Claude Code genegeerd; corrigeer namen indien nodig.

- [ ] **Step 1: Schrijf de falende test**

```python
# tests/test_claude_theme.py
import json

from livery import claude_theme


def test_theme_json_is_light_based_with_lighter_orange_user_bg():
    t = claude_theme.theme_json()
    assert t["name"] == "livery-claude"
    assert t["base"] == "light"
    ov = t["overrides"]
    # Jouw verzonden berichten: een lichter oranje dan de achtergrond.
    assert ov["userMessageBackground"].startswith("#")
    assert "text" in ov


def test_write_theme_creates_file(tmp_path):
    path = claude_theme.write_theme(tmp_path)
    assert path == tmp_path / "livery-claude.json"
    assert json.loads(path.read_text())["base"] == "light"


def test_activate_merges_and_preserves_existing_settings(tmp_path):
    settings = tmp_path / "settings.json"
    settings.write_text(json.dumps({"model": "opus", "theme": "dark"}))
    claude_theme.activate(settings)
    data = json.loads(settings.read_text())
    assert data["theme"] == "custom:livery-claude"  # gewijzigd
    assert data["model"] == "opus"                   # behouden


def test_activate_creates_settings_when_missing(tmp_path):
    settings = tmp_path / "sub" / "settings.json"
    claude_theme.activate(settings)
    assert json.loads(settings.read_text())["theme"] == "custom:livery-claude"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_claude_theme.py -v`
Expected: FAIL met `ModuleNotFoundError: No module named 'livery.claude_theme'`

- [ ] **Step 3: Schrijf de implementatie**

```python
# livery/claude_theme.py
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_claude_theme.py -v`
Expected: PASS (4 tests).

- [ ] **Step 5: Commit**

```bash
git add livery/claude_theme.py tests/test_claude_theme.py
git commit -m "feat: Claude Code thema + settings.json-activatie (merge)"
```

---

### Task 5: app — `_emit`-refactor + `cmd_command_start`

**Files:**
- Modify: `livery/app.py`
- Test: `tests/test_app.py`

**Interfaces:**
- Consumes: `profile.build_command_profile`, `profile.command_profile_name`, `profile.command_profile_file`, `commands.load`, bestaande `_detect`, `_emit`, `escapes`, `store`, `find_project_root`, `detect_theme`, `mute`.
- Produces:
  - `_emit(entry, theme, custom=None, profile=None, title_prefix="")` (uitgebreid, achterwaarts compatibel)
  - `cmd_command_start(name, cwd, profiles_dir, store_dir, session_dir, session_id, commands_path) -> str`
  - Constante `DEFAULT_COMMANDS_FILE = Path.home()/".config"/"livery"/"commands.json"`

- [ ] **Step 1: Schrijf de falende test**

```python
# tests/test_app.py  (voeg toe)
import json as _json

from livery import commands as _commands
from livery.profile import command_profile_name, command_profile_file


def _cmdfile(tmp_path, cfg=None):
    p = tmp_path / "commands.json"
    p.write_text(_json.dumps(cfg or _commands.DEFAULT_COMMANDS))
    return p


def test_command_start_prefixes_emoji_and_switches_profile(tmp_path, make_png, monkeypatch):
    monkeypatch.setattr(app, "detect_theme", lambda: "dark")
    monkeypatch.setattr(app, "color_from_png", lambda p: (40, 80, 200))
    (tmp_path / ".git").mkdir()
    (tmp_path / "site.webmanifest").write_text('{"icons":[{"src":"a.png"}]}')
    make_png(tmp_path / "a.png", (40, 80, 200))
    d = _dirs(tmp_path)
    app.cmd_emit(cwd=tmp_path, **d)  # projectprofiel + store vullen

    out = app.cmd_command_start(
        "claude", cwd=tmp_path, session_dir=tmp_path / "s", session_id=None,
        commands_path=_cmdfile(tmp_path), **d,
    )

    # Wisselt naar het commando-profiel en zet 🦀 vóór de projectnaam.
    assert f"SetProfile={command_profile_name('claude')}\007" in out
    assert f"]0;🦀 {tmp_path.resolve().name}\007" in out
    # Commando-profielbestand is geschreven.
    assert command_profile_file(d["profiles_dir"], "claude").exists()


def test_command_start_unknown_command_returns_empty(tmp_path):
    out = app.cmd_command_start(
        "nope", cwd=tmp_path, session_dir=tmp_path / "s", session_id=None,
        commands_path=_cmdfile(tmp_path), **_dirs(tmp_path),
    )
    assert out == ""
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_app.py -v -k command_start`
Expected: FAIL met `AttributeError: module 'livery.app' has no attribute 'cmd_command_start'`

- [ ] **Step 3: Schrijf de implementatie**

Vervang de bestaande `_emit` door onderstaande (achterwaarts compatibel — `profile=None, title_prefix=""` geeft exact het oude gedrag) en voeg `cmd_command_start` + import/constante toe.

```python
# livery/app.py  — bovenaan bij de imports:
from livery import commands
from livery.profile import (
    build_profile, build_command_profile, command_profile_name,
    command_profile_file, default_inherited_settings, profile_file, write_profile,
)

DEFAULT_COMMANDS_FILE = Path.home() / ".config" / "livery" / "commands.json"
```

```python
# livery/app.py  — vervang _emit:
def _emit(entry, theme, custom=None, profile=None, title_prefix=""):
    """Escape-output. `profile` overschrijft de profielnaam (bv. het
    commando-profiel); `title_prefix` plakt bv. '🦀 ' vóór de titel."""
    if entry.get("icon_path") and entry.get("dominant_color"):
        rgb = tuple(entry["dominant_color"])
        out = escapes.set_profile(profile or _profile_label(entry))
        out += escapes.tab_color(mute(rgb, theme, _tab_strength()))
    elif profile:
        out = escapes.set_profile(profile) + escapes.reset_tab_color()
    else:
        out = escapes.default_look()
    base = custom or _profile_label(entry)
    out += escapes.title(f"{title_prefix}{base}")
    return out
```

```python
# livery/app.py  — voeg toe:
def _ensure_command_profile(profiles_dir, name, bg_hex):
    if not command_profile_file(profiles_dir, name).exists():
        write_profile(profiles_dir, build_command_profile(name, bg_hex))
        time.sleep(_profile_delay())


def cmd_command_start(name, cwd, profiles_dir, store_dir,
                      session_dir=DEFAULT_SESSIONS, session_id=None,
                      commands_path=DEFAULT_COMMANDS_FILE):
    """Emit de tijdelijke commando-look: wissel naar het oranje profiel, behoud
    de projecttabkleur, en zet de commando-emoji vóór de titel."""
    cfg = commands.load(commands_path).get(name)
    if not cfg:
        return ""
    r, g, b = cfg.get("bg", [217, 119, 87])
    bg_hex = f"#{r:02X}{g:02X}{b:02X}"
    emoji = cfg.get("emoji", "")
    _ensure_command_profile(profiles_dir, name, bg_hex)

    theme = detect_theme()
    root = find_project_root(cwd)
    entry = store.read_entry(store_dir, root) or _detect(root) or {"root": str(root)}
    custom = store.read_custom(session_dir, session_id)
    prefix = f"{emoji} " if emoji else ""
    return _emit(entry, theme, custom, profile=command_profile_name(name), title_prefix=prefix)
```

- [ ] **Step 4: Run de volledige test-suite**

Run: `python3 -m pytest -v`
Expected: PASS — inclusief alle bestaande `test_app.py`-tests (de `_emit`-refactor mag niets breken).

- [ ] **Step 5: Commit**

```bash
git add livery/app.py tests/test_app.py
git commit -m "feat: cmd_command_start — oranje profielwissel + 🦀-titel"
```

---

### Task 6: CLI-subcommando's `command-start`, `commands`, `claude-setup`

**Files:**
- Modify: `livery/__main__.py`
- Modify: `livery/app.py` (voeg `cmd_commands`, `cmd_claude_setup` toe)
- Test: `tests/test_app.py`

**Interfaces:**
- Produces:
  - `app.cmd_commands(commands_path) -> str` — regels `naam\tfullscreen(0/1)`, één per commando.
  - `app.cmd_claude_setup(themes_dir, settings_path) -> str` — schrijft thema + activeert; geeft een bevestigingsregel.
  - CLI: `livery command-start <name>`, `livery commands`, `livery claude-setup`.

- [ ] **Step 1: Schrijf de falende test**

```python
# tests/test_app.py  (voeg toe)
def test_cmd_commands_lists_name_and_fullscreen_flag(tmp_path):
    out = app.cmd_commands(commands_path=_cmdfile(tmp_path))
    assert "claude\t1" in out.splitlines()


def test_cmd_claude_setup_writes_theme_and_activates(tmp_path):
    themes = tmp_path / "themes"
    settings = tmp_path / "settings.json"
    app.cmd_claude_setup(themes_dir=themes, settings_path=settings)
    assert (themes / "livery-claude.json").exists()
    assert _json.loads(settings.read_text())["theme"] == "custom:livery-claude"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_app.py -v -k "cmd_commands or claude_setup"`
Expected: FAIL met `AttributeError: ... 'cmd_commands'`

- [ ] **Step 3: Schrijf de implementatie**

```python
# livery/app.py  — voeg imports + functies toe:
from livery import claude_theme

DEFAULT_THEMES = Path.home() / ".claude" / "themes"
DEFAULT_SETTINGS_FILE = Path.home() / ".claude" / "settings.json"


def cmd_commands(commands_path=DEFAULT_COMMANDS_FILE):
    cfg = commands.ensure(commands_path)
    lines = []
    for name, spec in cfg.items():
        fs = "1" if spec.get("fullscreen") else "0"
        lines.append(f"{name}\t{fs}")
    return "\n".join(lines) + ("\n" if lines else "")


def cmd_claude_setup(themes_dir=DEFAULT_THEMES, settings_path=DEFAULT_SETTINGS_FILE):
    path = claude_theme.write_theme(themes_dir)
    claude_theme.activate(settings_path)
    return f"livery-claude thema geschreven ({path}) en geactiveerd in {settings_path}\n"
```

```python
# livery/__main__.py  — voeg parsers toe (na de bestaande sub.add_parser-regels):
    p_cmd = sub.add_parser("command-start", parents=[common])
    p_cmd.add_argument("name")
    sub.add_parser("commands", parents=[common])
    sub.add_parser("claude-setup", parents=[common])
```

```python
# livery/__main__.py  — voeg dispatch toe (in de if/elif-keten):
    elif a.cmd == "command-start":
        sys.stdout.write(app.cmd_command_start(a.name, cwd=a.cwd, **dirs, **sess))
    elif a.cmd == "commands":
        sys.stdout.write(app.cmd_commands())
    elif a.cmd == "claude-setup":
        sys.stdout.write(app.cmd_claude_setup())
```

> Let op: `cmd_command_start` accepteert `commands_path`; de CLI gebruikt de
> default. `**dirs` levert `profiles_dir`/`store_dir`, `**sess` levert
> `session_dir`/`session_id` (net als de bestaande subcommando's).

- [ ] **Step 4: Run de volledige suite + een CLI-rooktest**

Run: `python3 -m pytest -v`
Expected: PASS.

Run: `PYTHONPATH=. python3 -m livery commands`
Expected: uitvoer bevat de regel `claude\t1`.

- [ ] **Step 5: Commit**

```bash
git add livery/__main__.py livery/app.py tests/test_app.py
git commit -m "feat: CLI command-start/commands/claude-setup"
```

---

### Task 7: zsh — wrapper-generatie

**Files:**
- Modify: `livery.zsh`

**Interfaces:**
- Consumes: `livery command-start <name>`, `livery commands`, bestaande `_livery_py`, `_livery_run`.

> **Geen unit-test** (zsh); geverifieerd in Task 8. De loop gebruikt
> process-substitutie (`< <(...)`) zodat de functie-definities in de huidige
> shell landen (een `| while`-pipe draait in een subshell en zou de functies
> verliezen).

- [ ] **Step 1: Voeg de wrapper-generatie toe aan `livery.zsh`**

Voeg dit toe vóór de bestaande `add-zsh-hook chpwd _livery_run`-regel:

```zsh
# --- commando-wrappers: tijdelijke "AI-look" per invocation (bv. `claude`) ---
# Voor elk commando in ~/.config/livery/commands.json definiëren we een functie
# die de look aanzet, het echte commando draait, en na afloop (ook bij Ctrl-C,
# via `always`) de normale look herstelt.
_livery_define_wrappers() {
  [[ "$TERM_PROGRAM" == "iTerm.app" ]] || return 0
  local name fs env
  while IFS=$'\t' read -r name fs; do
    [[ -n "$name" ]] || continue
    env=""
    [[ "$fs" == "1" ]] && env="CLAUDE_CODE_NO_FLICKER=1 "  # fullscreen (Task 8: verifieer)
    eval "
    ${name}() {
      print -rn -- \"\$(_livery_py command-start ${name} --cwd \"\$PWD\" --session \"\$ITERM_SESSION_ID\" 2>/dev/null)\"
      {
        ${env}command ${name} \"\$@\"
      } always {
        _livery_run
      }
    }
    "
  done < <(_livery_py commands 2>/dev/null)
}
_livery_define_wrappers
```

- [ ] **Step 2: Syntax-check het script**

Run: `zsh -n livery.zsh`
Expected: geen uitvoer (geen syntaxfouten).

- [ ] **Step 3: Verifieer dat de functie in een echte shell wordt gedefinieerd**

Run:
```bash
TERM_PROGRAM=iTerm.app ITERM_SESSION_ID=w0t0p0 zsh -ic 'source ./livery.zsh; whence -w claude'
```
Expected: `claude: function`

- [ ] **Step 4: Commit**

```bash
git add livery.zsh
git commit -m "feat: zsh-wrappers uit commands.json (claude → AI-look)"
```

---

### Task 8: End-to-end verificatie in iTerm2 + tuning

**Files:** (alleen aanpassingen n.a.v. bevindingen)

> Dit is een **handmatige** verificatietaak. Voer 'm uit in een echte
> iTerm2-sessie. Noteer bevindingen; pas kleuren/tokens/env-var aan waar nodig
> en commit die aanpassingen.

- [ ] **Step 1: Setup draaien**

Run (in iTerm2, met `source .../livery.zsh` geladen):
```bash
livery claude-setup
```
Verifieer: `~/.claude/themes/livery-claude.json` bestaat en `~/.claude/settings.json` bevat `"theme": "custom:livery-claude"` (overige sleutels intact).

- [ ] **Step 2: Claude-modus visueel checken**

`cd` naar een git-project met favicon → normale projectlook. Start `claude`.
Verifieer:
  - venster wordt **oranje** (`#D97757`), ook als systeem dark/light is;
  - de tab-titel begint met **🦀**;
  - de **tabkleur** is nog de projectkleur;
  - **alle tekst** (prompt, output, statusline) is leesbaar op het oranje — zo niet, verlaag de betreffende `ANSI`/`FOREGROUND`-waarden in `livery/palette.py` (test `test_palette.py` moet blijven slagen) of pas de tokens in `claude_theme.py` aan.

- [ ] **Step 3: Fullscreen + `userMessageBackground` verifiëren**

Bevestig dat claude in **fullscreen** draait en dat jouw verzonden berichten een **lichter-oranje** achtergrond hebben. Klopt de env-var niet (geen fullscreen), zoek de juiste schakelaar (`/tui fullscreen`, alternatieve env-var of settings-sleutel) en pas de mapping in `livery.zsh` (Task 7, Step 1) aan. Verifieer met `/theme` dat het `livery-claude`-thema laadt en corrigeer eventuele token-namen in `claude_theme.py`.

- [ ] **Step 4: Herstel verifiëren (normaal + Ctrl-C)**

Sluit claude normaal af → tab valt terug op de projectlook (profiel, projectkleur, titel **zonder** 🦀). Herhaal en breek af met **Ctrl-C** tijdens een claude-run → ook dan moet de normale look terugkomen (dankzij het `always`-blok). Test ook: `cd` naar een andere map tijdens de sessie, dan afsluiten → look van de nieuwe map.

- [ ] **Step 5: Bevestig dat claude de titel niet overschrijft**

Terwijl claude draait: blijft de 🦀-titel staan? Zo niet (claude zet toch een OSC-titel), documenteer dit als bekende beperking in de spec en overweeg de titel na launch opnieuw te zetten.

- [ ] **Step 6: Commit eventuele tuning**

```bash
git add -A
git commit -m "chore: Claude-modus kleuren/tokens/env getuned na iTerm-verificatie"
```

---

### Task 9: README — sectie Claude-modus

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Voeg een korte, duidelijke sectie toe** (na "Commando's")

```markdown
## Claude-modus

Start je `claude`, dan krijgt de tab tijdelijk een **Claude-oranje** look met een
🦀 vóór de titel — los van je projectprofiel. Sluit je claude af, dan komt de
normale projectlook terug. De projecttabkleur blijft zichtbaar, zodat je bij
meerdere claude-tabs ziet welk project het is.

Eenmalig instellen (schrijft een Claude Code-thema en activeert het):

    livery claude-setup

Claude draait in **fullscreen** (nodig voor de gekleurde achtergrond achter je
eigen berichten). Andere commando's een eigen look geven? Voeg een regel toe aan
`~/.config/livery/commands.json`:

    { "claude": { "emoji": "🦀", "bg": [217, 119, 87], "fullscreen": true } }
```

- [ ] **Step 2: Controleer de lengte/duidelijkheid**

Lees de sectie terug: kort, geen overbodige uitleg, klopt met het gedrag. Pas in.

- [ ] **Step 3: Commit**

```bash
git add README.md
git commit -m "docs: README-sectie Claude-modus"
```

---

## Self-Review (uitgevoerd)

**Spec-dekking:** Deel A (oranje profiel + palet) → Task 1,2,5,7. Titel-🦀 → Task 5,7. Projecttabkleur behouden → Task 5. Deel B (thema + activatie + fullscreen) → Task 4,6,7,8. Per-commando config → Task 3,6,7. `claude-setup` → Task 4,6. Herstel bij afsluiten/Ctrl-C → Task 7,8. README + fullscreen-notitie → Task 9. Geverifieerde onzekerheden (fullscreen-mechanisme, titel-gedrag) → Task 8. **Geen gaten.**

**Placeholder-scan:** geen TBD/TODO in code-stappen; alle code is concreet. De enige "verifieer later"-punten (token-namen, fullscreen-env-var) zijn expliciet als handmatige verificatiestappen in Task 8 belegd, met concrete fallback-acties — geen code-placeholders.

**Type-consistentie:** `command_profile_name`/`command_profile_file`/`build_command_profile` gelijk benoemd in Task 2, 5, 6. `commands.load`/`ensure` gelijk in Task 3, 5, 6. `claude_theme.write_theme`/`activate`/`theme_json`/`SLUG` gelijk in Task 4, 6. `_emit(entry, theme, custom=None, profile=None, title_prefix="")` consistent gebruikt in Task 5. CLI-namen (`command-start`, `commands`, `claude-setup`) consistent tussen zsh (Task 7) en `__main__` (Task 6).

---

### Task 10: dev/watch-wrappers (👷 geel) + `run`-veld + alias-overname

**Files:**
- Modify: `livery/commands.py` (DEFAULT_COMMANDS)
- Modify: `livery/app.py` (`cmd_commands` output: 3e veld `run`)
- Modify: `livery.zsh` (`_livery_define_wrappers`: 3 velden lezen, `unalias`, `run` uitvoeren)
- Modify: `README.md` (commands.json-voorbeeld met dev/watch + uitleg `run`)
- Test: `tests/test_commands.py`, `tests/test_app.py`

**Achtergrond:** De gebruiker typt `dev` en `watch` — beide zsh-aliases naar
`npm run dev` / `npm run watch` (geen losse binary). Een alias wordt vóór een
functie uitgeklapt, dus livery moet de alias `unalias`en en zelf een functie
neerzetten die het echte commando (`run`) draait. livery wordt als laatste
gesourcet in `.zshrc`, dus `unalias` bij source-tijd blijft plakken. Geel =
`rgb(255,231,93)` = `#FFE75D`; het bestaande donkere palet is leesbaar op geel
(hoger contrast dan op oranje). Geen fullscreen voor dev/watch.

**Interfaces:**
- `commands.DEFAULT_COMMANDS` bevat nu ook `dev` en `watch` met een `run`-veld.
- `cmd_commands` output-regel wordt `naam\tfullscreen\trun` (run leeg indien afwezig).
- zsh leest 3 velden; per naam: `unalias`, dan functie die `run` (of `command <naam>`) draait.

- [ ] **Step 1: Update de commands-test (RED)**

```python
# tests/test_commands.py  (voeg toe)
def test_defaults_include_dev_and_watch_with_run():
    d = commands.DEFAULT_COMMANDS
    assert d["dev"] == {"emoji": "👷‍♂️", "bg": [255, 231, 93], "run": "npm run dev"}
    assert d["watch"] == {"emoji": "👷‍♂️", "bg": [255, 231, 93], "run": "npm run watch"}
```

En pas de bestaande app-test aan het nieuwe 3-velden-formaat aan:

```python
# tests/test_app.py  — vervang de asserts in test_cmd_commands_lists_name_and_fullscreen_flag:
def test_cmd_commands_lists_name_and_fullscreen_flag(tmp_path):
    out = app.cmd_commands(commands_path=_cmdfile(tmp_path))
    lines = out.splitlines()
    assert "claude\t1\t" in lines               # fullscreen, geen run
    assert "dev\t0\tnpm run dev" in lines        # niet-fullscreen, met run
    assert "watch\t0\tnpm run watch" in lines
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_commands.py tests/test_app.py -v -k "dev_and_watch or cmd_commands"`
Expected: FAIL (defaults missen dev/watch; oude output heeft geen 3e veld).

- [ ] **Step 3: Implementeer**

```python
# livery/commands.py  — vervang DEFAULT_COMMANDS:
DEFAULT_COMMANDS = {
    "claude": {"emoji": "🦀", "bg": [217, 119, 87], "fullscreen": True},
    "dev": {"emoji": "👷‍♂️", "bg": [255, 231, 93], "run": "npm run dev"},
    "watch": {"emoji": "👷‍♂️", "bg": [255, 231, 93], "run": "npm run watch"},
}
```

```python
# livery/app.py  — vervang cmd_commands:
def cmd_commands(commands_path=DEFAULT_COMMANDS_FILE):
    cfg = commands.ensure(commands_path)
    lines = []
    for name, spec in cfg.items():
        fs = "1" if spec.get("fullscreen") else "0"
        run = spec.get("run", "")
        lines.append(f"{name}\t{fs}\t{run}")
    return "\n".join(lines) + ("\n" if lines else "")
```

```zsh
# livery.zsh  — vervang _livery_define_wrappers volledig:
_livery_define_wrappers() {
  [[ "$TERM_PROGRAM" == "iTerm.app" ]] || return 0
  local name fs run env exec_cmd
  while IFS=$'\t' read -r name fs run; do
    [[ -n "$name" ]] || continue
    unalias "$name" 2>/dev/null   # bv. dev='npm run dev' mag de functie niet overschaduwen
    env=""
    [[ "$fs" == "1" ]] && env="CLAUDE_CODE_NO_FLICKER=1 "  # fullscreen (Task 8: verifieer)
    if [[ -n "$run" ]]; then exec_cmd="$run"; else exec_cmd="command $name"; fi
    eval "
    ${name}() {
      print -rn -- \"\$(_livery_py command-start ${name} --cwd \"\$PWD\" --session \"\$ITERM_SESSION_ID\" 2>/dev/null)\"
      {
        ${env}${exec_cmd} \"\$@\"
      } always {
        local rc=\$?
        _livery_run
        return \$rc
      }
    }
    "
  done < <(_livery_py commands 2>/dev/null)
}
```

- [ ] **Step 4: Run tests + zsh-checks**

Run: `python3 -m pytest` → alle tests PASS.
Run: `zsh -n livery.zsh` → geen output.
Run: `TERM_PROGRAM=iTerm.app ITERM_SESSION_ID=w0t0p0 zsh -ic 'alias dev="npm run dev"; source ./livery.zsh; whence -w dev'`
Expected: `dev: function` (de alias is overgenomen door de functie).

- [ ] **Step 5: README-voorbeeld bijwerken**

Vervang het commands.json-voorbeeld in de Claude-modus-sectie door:

```json
{
  "claude": { "emoji": "🦀", "bg": [217, 119, 87], "fullscreen": true },
  "dev":    { "emoji": "👷‍♂️", "bg": [255, 231, 93], "run": "npm run dev" },
  "watch":  { "emoji": "👷‍♂️", "bg": [255, 231, 93], "run": "npm run watch" }
}
```

En één regel uitleg: een commando met een `run`-veld draait dát in plaats van
een gelijknamige binary, en livery neemt een gelijknamige alias over.

- [ ] **Step 6: Commit**

```bash
git add livery/commands.py livery/app.py livery.zsh README.md tests/
git commit -m "feat: dev/watch-wrappers (👷 geel) met run-veld en alias-overname"
```
