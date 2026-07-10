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
    assert "🦀" in p.read_text()  # literal emoji in raw bytes (ensure_ascii=False), niet \uXXXX
    assert cfg["claude"]["fullscreen"] is True


def test_defaults_include_dev_and_watch_with_run():
    d = commands.DEFAULT_COMMANDS
    assert d["dev"] == {"emoji": "👷‍♂️", "bg": [255, 231, 93], "run": "npm run dev"}
    assert d["watch"] == {"emoji": "👷‍♂️", "bg": [255, 231, 93], "run": "npm run watch"}
