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
