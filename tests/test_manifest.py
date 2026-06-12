from pathlib import Path

from livery.manifest import find_manifest


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


from livery.manifest import first_png


def test_first_png_relative_src(tmp_path):
    m = tmp_path / "site.webmanifest"
    m.write_text('{"icons":[{"src":"icons/a.png"}]}')
    assert first_png(m) == (tmp_path / "icons" / "a.png").resolve()


def test_first_png_web_absolute_src(tmp_path):
    m = tmp_path / "site.webmanifest"
    m.write_text('{"icons":[{"src":"/android-chrome-192.png"}]}')
    assert first_png(m) == (tmp_path / "android-chrome-192.png").resolve()


def test_first_png_skips_non_png(tmp_path):
    m = tmp_path / "site.webmanifest"
    m.write_text('{"icons":[{"src":"a.svg"},{"src":"b.png"}]}')
    assert first_png(m) == (tmp_path / "b.png").resolve()


def test_first_png_none_when_no_png(tmp_path):
    m = tmp_path / "site.webmanifest"
    m.write_text('{"icons":[{"src":"a.svg"}]}')
    assert first_png(m) is None


def test_first_png_invalid_json(tmp_path):
    m = tmp_path / "site.webmanifest"
    m.write_text("{ not json")
    assert first_png(m) is None
