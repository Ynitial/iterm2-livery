import os

from iterm_favicon import app, escapes, store
from iterm_favicon.profile import profile_file


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
    assert "SetProfile=favicon:" in out
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
    assert "SetProfile=favicon:" in out


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


def test_reeval_overwrites_entry_keeps_custom(tmp_path, make_png, monkeypatch):
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
    app.cmd_reeval(cwd=tmp_path, **d)
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


import subprocess
import sys
from pathlib import Path


def test_cli_emit_not_a_project_prints_reset(tmp_path):
    repo = Path(__file__).resolve().parent.parent
    proc = subprocess.run(
        [sys.executable, "-m", "iterm_favicon", "emit",
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
        [sys.executable, "-m", "iterm_favicon", "rename", "dev",
         "--cwd", str(tmp_path),
         "--profiles-dir", str(tmp_path / "p"),
         "--store-dir", str(tmp_path / "s")],
        cwd=repo, env=dict(os.environ), capture_output=True, text=True,
    )
    assert proc.returncode == 0
    assert "]0;EnvApp | dev\007" in proc.stdout
