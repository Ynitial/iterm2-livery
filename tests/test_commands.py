import json

from livery import commands


def test_load_missing_returns_defaults(tmp_path):
    cfg = commands.load(tmp_path / "nope.json")
    assert cfg["claude"]["emoji"] == "🦀"
    assert cfg["claude"]["bg"] == [24, 36, 44]
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
    assert "🦀" in p.read_text()  # literal emoji in raw bytes (ensure_ascii=False), niet \uXXXX
    assert cfg["claude"]["fullscreen"] is True


def test_defaults_include_dev_and_watch_with_run():
    d = commands.DEFAULT_COMMANDS
    assert d["dev"] == {"emoji": "👷‍♂️", "bg": [255, 231, 93], "run": "npm run dev"}
    assert d["watch"] == {"emoji": "👷‍♂️", "bg": [255, 231, 93], "run": "npm run watch"}


def test_load_merges_defaults_into_stale_user_file(tmp_path):
    # Regressie: een gebruiker-config van vóór de introductie van dev/watch
    # mag die nieuwe commando's niet stilzwijgend laten verdwijnen.
    p = tmp_path / "commands.json"
    p.write_text(json.dumps({"claude": {"emoji": "🦀", "bg": [217, 119, 87], "fullscreen": True}}))
    cfg = commands.load(p)
    assert "dev" in cfg
    assert "watch" in cfg


def test_load_user_entry_overrides_default(tmp_path):
    p = tmp_path / "commands.json"
    p.write_text(json.dumps({"claude": {"emoji": "X", "bg": [1, 2, 3], "fullscreen": False}}))
    cfg = commands.load(p)
    assert cfg["claude"]["emoji"] == "X"
    assert "dev" in cfg


def test_load_does_not_mutate_module_defaults(tmp_path):
    p = tmp_path / "commands.json"
    p.write_text(json.dumps({"claude": {"emoji": "X", "bg": [1, 2, 3], "fullscreen": False}}))
    commands.load(p)
    assert commands.DEFAULT_COMMANDS["claude"]["emoji"] == "🦀"
