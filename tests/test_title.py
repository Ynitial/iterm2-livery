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
