import os

from livery import app, escapes, store
from livery.profile import profile_file
from livery.tint import mute

import json as _json

from livery import commands as _commands
from livery.profile import command_profile_name, command_profile_file


def _dirs(tmp_path):
    return {"profiles_dir": tmp_path / "profiles", "store_dir": tmp_path / "store"}


def _cmdfile(tmp_path, cfg=None):
    p = tmp_path / "commands.json"
    p.write_text(_json.dumps(cfg or _commands.DEFAULT_COMMANDS))
    return p


def test_emit_not_a_project_resets(tmp_path, monkeypatch):
    monkeypatch.setattr(app, "detect_theme", lambda: "dark")
    out = app.cmd_emit(cwd=tmp_path, **_dirs(tmp_path))
    # Niet-project: titel wissen (iTerm default) + default-look, geen store-entry.
    assert out == escapes.reset()
    assert app.store.read_entry(_dirs(tmp_path)["store_dir"], tmp_path.resolve()) is None


def test_emit_manifest_sets_icon_color_and_title(tmp_path, make_png, monkeypatch):
    monkeypatch.setattr(app, "detect_theme", lambda: "dark")
    monkeypatch.setattr(app, "color_from_png", lambda p: (40, 80, 200))
    (tmp_path / "site.webmanifest").write_text('{"name":"Slowboard","icons":[{"src":"a.png"}]}')
    make_png(tmp_path / "a.png", (40, 80, 200))
    d = _dirs(tmp_path)

    out = app.cmd_emit(cwd=tmp_path, **d)

    assert f"]0;{tmp_path.resolve().name}\007" in out  # sessienaam = mapnaam (geen rename)
    assert f"SetProfile={tmp_path.resolve().name}\007" in out  # profielnaam = mapnaam
    entry = store.read_entry(d["store_dir"], tmp_path.resolve())
    assert entry["dominant_color"] == [40, 80, 200]
    assert entry["name"] == tmp_path.resolve().name
    assert entry["source"] == "manifest"
    assert profile_file(d["profiles_dir"], tmp_path.resolve()).exists()


def test_emit_env_only_sets_title_no_icon(tmp_path, monkeypatch):
    monkeypatch.setattr(app, "detect_theme", lambda: "dark")
    (tmp_path / ".env").write_text("APP_NAME=EnvApp\n")
    d = _dirs(tmp_path)

    out = app.cmd_emit(cwd=tmp_path, **d)

    assert f"]0;{tmp_path.resolve().name}\007" in out  # titel = mapnaam, niet .env-naam
    assert "SetProfile=Default" in out
    entry = store.read_entry(d["store_dir"], tmp_path.resolve())
    assert entry["icon_path"] is None
    assert entry["name"] == tmp_path.resolve().name
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
    # geen rescan; titel + profiel = mapnaam (profiel-label)
    assert f"]0;{tmp_path.resolve().name}\007" in out
    assert f"SetProfile={tmp_path.resolve().name}\007" in out


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


def test_scan_overwrites_entry(tmp_path, make_png, monkeypatch):
    monkeypatch.setattr(app, "detect_theme", lambda: "dark")
    d = _dirs(tmp_path)
    (tmp_path / "site.webmanifest").write_text('{"name":"Slow","icons":[{"src":"a.png"}]}')
    make_png(tmp_path / "a.png", (10, 10, 200))
    store.write_entry(d["store_dir"], tmp_path.resolve(), {
        "root": str(tmp_path.resolve()), "icon_path": "/old.png",
        "dominant_color": [1, 1, 1], "name": "Old",
        "source": "manifest", "last_theme": "dark",
    })
    monkeypatch.setattr(app, "color_from_png", lambda p: (10, 10, 200))
    app.cmd_scan(cwd=tmp_path, **d)
    entry = store.read_entry(d["store_dir"], tmp_path.resolve())
    assert entry["dominant_color"] == [10, 10, 200]
    assert entry["icon_path"].endswith("a.png")
    assert entry["name"] == tmp_path.resolve().name


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


def test_rename_sets_session_name_per_tab(tmp_path, monkeypatch):
    monkeypatch.setattr(app, "detect_theme", lambda: "dark")
    d = _dirs(tmp_path)
    sdir = tmp_path / "sessions"
    (tmp_path / ".env").write_text("APP_NAME=EnvApp\n")
    # rename zet de sessienaam = de custom (per tab), niet 'mapnaam | custom'
    out = app.cmd_rename("dev", cwd=tmp_path, session_dir=sdir, session_id="w0t1", **d)
    assert "]0;dev\007" in out
    assert store.read_custom(sdir, "w0t1") == "dev"
    # leeg argument wist 'm
    app.cmd_rename("", cwd=tmp_path, session_dir=sdir, session_id="w0t1", **d)
    assert store.read_custom(sdir, "w0t1") is None


def test_rename_is_per_session(tmp_path, monkeypatch):
    monkeypatch.setattr(app, "detect_theme", lambda: "dark")
    d = _dirs(tmp_path)
    sdir = tmp_path / "sessions"
    app.cmd_rename("A", cwd=tmp_path, session_dir=sdir, session_id="tabA", **d)
    app.cmd_rename("B", cwd=tmp_path, session_dir=sdir, session_id="tabB", **d)
    # twee tabs in dezelfde map -> elk een eigen naam
    assert store.read_custom(sdir, "tabA") == "A"
    assert store.read_custom(sdir, "tabB") == "B"


def test_emit_uses_session_custom(tmp_path, make_png, monkeypatch):
    monkeypatch.setattr(app, "detect_theme", lambda: "dark")
    monkeypatch.setattr(app, "color_from_png", lambda p: (40, 80, 200))
    (tmp_path / "site.webmanifest").write_text('{"icons":[{"src":"a.png"}]}')
    make_png(tmp_path / "a.png", (40, 80, 200))
    d = _dirs(tmp_path)
    sdir = tmp_path / "sessions"
    store.write_custom(sdir, "tabA", "feature")
    out = app.cmd_emit(cwd=tmp_path, session_dir=sdir, session_id="tabA", **d)
    assert "]0;feature\007" in out  # sessienaam uit de per-tab store
    # andere tab (geen custom) -> mapnaam
    out2 = app.cmd_emit(cwd=tmp_path, session_dir=sdir, session_id="tabB", **d)
    assert f"]0;{tmp_path.resolve().name}\007" in out2


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
         "--store-dir", str(tmp_path / "s"),
         "--session-dir", str(tmp_path / "sess"), "--session", "w0t1"],
        cwd=repo, env=dict(os.environ), capture_output=True, text=True,
    )
    assert proc.returncode == 0
    assert "]0;dev\007" in proc.stdout


def test_rename_does_not_rewrite_existing_profile(tmp_path, make_png, monkeypatch):
    # Renamen in tab A mag het gedeelde profiel niet herschrijven (zou tab B resetten).
    monkeypatch.setattr(app, "detect_theme", lambda: "dark")
    monkeypatch.setattr(app, "color_from_png", lambda p: (40, 80, 200))
    (tmp_path / "site.webmanifest").write_text('{"icons":[{"src":"a.png"}]}')
    make_png(tmp_path / "a.png", (40, 80, 200))
    d = _dirs(tmp_path)
    sdir = tmp_path / "sessions"
    app.cmd_emit(cwd=tmp_path, session_dir=sdir, session_id="t1", **d)  # schrijft profiel
    calls = []
    monkeypatch.setattr(app, "_ensure_profile", lambda *a, **k: calls.append(1))
    app.cmd_rename("dev", cwd=tmp_path, session_dir=sdir, session_id="t1", **d)
    assert calls == []  # bestaand profiel niet opnieuw geschreven


def test_rename_project_sets_profile_label(tmp_path, make_png, monkeypatch):
    monkeypatch.setattr(app, "detect_theme", lambda: "dark")
    monkeypatch.setattr(app, "color_from_png", lambda p: (40, 80, 200))
    (tmp_path / "site.webmanifest").write_text('{"icons":[{"src":"a.png"}]}')
    make_png(tmp_path / "a.png", (40, 80, 200))
    d = _dirs(tmp_path)
    sdir = tmp_path / "sessions"
    out = app.cmd_rename("Krabben", cwd=tmp_path, session_dir=sdir, session_id="t1",
                         project=True, **d)
    # profielnaam (project) = Krabben; geldt projectbreed (in de store)
    assert "SetProfile=Krabben\007" in out
    assert store.read_entry(d["store_dir"], tmp_path.resolve())["label"] == "Krabben"
    # tab-rename blijft per sessie en los van het project-label
    app.cmd_rename("dev", cwd=tmp_path, session_dir=sdir, session_id="t1", **d)
    assert store.read_custom(sdir, "t1") == "dev"
    assert store.read_entry(d["store_dir"], tmp_path.resolve())["label"] == "Krabben"


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
    # Project-tabkleur blijft behouden (niet vervangen door oranje bg).
    assert escapes.tab_color(mute((40, 80, 200), "dark", 1.0)) in out


def test_command_start_unknown_command_returns_empty(tmp_path):
    out = app.cmd_command_start(
        "nope", cwd=tmp_path, session_dir=tmp_path / "s", session_id=None,
        commands_path=_cmdfile(tmp_path), **_dirs(tmp_path),
    )
    assert out == ""


def test_command_start_non_project_falls_back_to_reset_tab_color(tmp_path, monkeypatch):
    monkeypatch.setattr(app, "detect_theme", lambda: "dark")
    d = _dirs(tmp_path)

    out = app.cmd_command_start(
        "claude", cwd=tmp_path, session_dir=tmp_path / "s", session_id=None,
        commands_path=_cmdfile(tmp_path), **d,
    )

    # Wisselt naar het commando-profiel.
    assert f"SetProfile={command_profile_name('claude')}\007" in out
    # Geen project: tab-kleur resetten.
    assert escapes.reset_tab_color() in out
    # Titel geeft aan dat we in een commando zijn (🦀 prefix), geen project-tabkleur.
    assert "]0;🦀 " in out
    assert ";bg;red;brightness;" not in out
