import json

from livery import claude_theme


def test_theme_json_is_dark_based_with_light_text_and_user_bg():
    t = claude_theme.theme_json()
    assert t["name"] == "livery-claude"
    assert t["base"] == "dark"
    ov = t["overrides"]
    # Donkere achtergrond → lichte tekst en een eigen-berichten-vlak.
    assert ov["userMessageBackground"].startswith("#")
    assert ov["text"] == "#F3E7E0"


def test_write_theme_creates_file(tmp_path):
    path = claude_theme.write_theme(tmp_path)
    assert path == tmp_path / "livery-claude.json"
    assert json.loads(path.read_text())["base"] == "dark"


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


def test_activate_recovers_from_malformed_json(tmp_path):
    settings = tmp_path / "settings.json"
    settings.write_text("{not json")
    claude_theme.activate(settings)
    data = json.loads(settings.read_text())
    assert data["theme"] == "custom:livery-claude"


def test_activate_recovers_from_non_dict_json(tmp_path):
    settings = tmp_path / "settings.json"
    settings.write_text("[1, 2, 3]")
    claude_theme.activate(settings)
    data = json.loads(settings.read_text())
    assert data["theme"] == "custom:livery-claude"
