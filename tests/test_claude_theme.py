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
