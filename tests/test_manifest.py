from pathlib import Path

from livery.manifest import find_manifest


def test_finds_manifest_in_root(tmp_path):
    m = tmp_path / "site.webmanifest"
    m.write_text("{}")
    assert find_manifest(tmp_path) == m


def test_finds_manifest_in_public(tmp_path):
    pub = tmp_path / "public"
    pub.mkdir()
    m = pub / "site.webmanifest"
    m.write_text("{}")
    assert find_manifest(tmp_path) == m


def test_no_deep_search_without_git(tmp_path):
    # Diep manifest, geen .git -> map wordt NIET afgestruind.
    deep = tmp_path / "a" / "b" / "c"
    deep.mkdir(parents=True)
    (deep / "site.webmanifest").write_text("{}")
    assert find_manifest(tmp_path) is None


def test_deep_search_with_git(tmp_path):
    (tmp_path / ".git").mkdir()
    deep = tmp_path / "a" / "b" / "c"
    deep.mkdir(parents=True)
    m = deep / "site.webmanifest"
    m.write_text("{}")
    assert find_manifest(tmp_path) == m


def test_prunes_node_modules_even_with_git(tmp_path):
    (tmp_path / ".git").mkdir()
    nm = tmp_path / "node_modules" / "pkg"
    nm.mkdir(parents=True)
    (nm / "site.webmanifest").write_text("{}")
    assert find_manifest(tmp_path) is None


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
