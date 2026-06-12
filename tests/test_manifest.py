from pathlib import Path

from iterm_favicon.manifest import find_manifest


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
