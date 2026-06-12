from iterm_favicon.store import iter_entries, read_entry, store_path, write_entry


def test_write_then_read(tmp_path):
    entry = {"root": "/x", "icon_path": "/x/a.png",
             "dominant_color": [10, 20, 30], "source": "manifest", "last_theme": "dark"}
    write_entry(tmp_path, "/x", entry)
    assert read_entry(tmp_path, "/x") == entry


def test_read_missing_returns_none(tmp_path):
    assert read_entry(tmp_path, "/nope") is None


def test_store_path_stable_per_root(tmp_path):
    assert store_path(tmp_path, "/x") == store_path(tmp_path, "/x")
    assert store_path(tmp_path, "/x") != store_path(tmp_path, "/y")


def test_iter_entries(tmp_path):
    write_entry(tmp_path, "/a", {"root": "/a"})
    write_entry(tmp_path, "/b", {"root": "/b"})
    roots = sorted(e["root"] for e in iter_entries(tmp_path))
    assert roots == ["/a", "/b"]
