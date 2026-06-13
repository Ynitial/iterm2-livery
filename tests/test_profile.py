import json
import plistlib

from livery.profile import (
    build_profile, default_inherited_settings, profile_file, profile_guid,
    profile_name, write_profile,
)


def test_profile_name_uses_root_basename():
    assert profile_name("/Users/yoni/projects/slowboard") == "slowboard"


def test_guid_stable_per_root():
    assert profile_guid("/x") == profile_guid("/x")
    assert profile_guid("/x") != profile_guid("/y")


def test_build_profile_has_icon_and_tab_color():
    p = build_profile("/x/proj", "/x/proj/a.png", (255, 0, 0))
    assert p["Icon"] == 2
    assert p["Custom Icon Path"] == "/x/proj/a.png"
    assert p["Use Tab Color"] is True
    assert p["Dynamic Profile Parent Name"] == "Default"
    assert abs(p["Tab Color"]["Red Component"] - 1.0) < 1e-6
    # geen achtergrond-tint meer -> erft de standaard-achtergrond
    assert "Background Color" not in p
    # Title Components zetten we niet; dat erven we van het Default-profiel
    assert "Title Components" not in p


def test_build_profile_merges_color_settings():
    colors = {
        "Use Separate Colors for Light and Dark Mode": True,
        "Background Color (Dark)": {"Red Component": 0.08},
    }
    p = build_profile("/x/proj", "/x/proj/a.png", (255, 0, 0), colors)
    assert p["Use Separate Colors for Light and Dark Mode"] is True
    assert p["Background Color (Dark)"] == {"Red Component": 0.08}
    assert p["Tab Color"]["Red Component"] == 1.0  # tabkleur blijft overschreven


def test_default_inherited_settings_reads_default_profile(tmp_path):
    prefs = tmp_path / "iterm.plist"
    data = {
        "Default Bookmark Guid": "G1",
        "New Bookmarks": [
            {"Guid": "G0", "Name": "Other", "Background Color (Dark)": {"Red Component": 0.5}},
            {"Guid": "G1", "Name": "Default",
             "Use Separate Colors for Light and Dark Mode": True,
             "Background Color (Dark)": {"Red Component": 0.08},
             "Foreground Color (Dark)": {"Red Component": 0.86},
             "Irrelevant Key": 123},
        ],
    }
    with open(prefs, "wb") as f:
        plistlib.dump(data, f)
    cs = default_inherited_settings(prefs)
    assert cs["Use Separate Colors for Light and Dark Mode"] is True
    assert cs["Background Color (Dark)"] == {"Red Component": 0.08}
    assert cs["Foreground Color (Dark)"] == {"Red Component": 0.86}
    assert "Irrelevant Key" not in cs


def test_default_inherited_settings_missing_prefs_returns_empty(tmp_path):
    assert default_inherited_settings(tmp_path / "nope.plist") == {}


def test_write_profile_wraps_in_profiles_array(tmp_path):
    p = build_profile("/x/proj", "/x/proj/a.png", (1, 2, 3))
    write_profile(tmp_path, p)
    written = json.loads(profile_file(tmp_path, "/x/proj").read_text())
    assert written["Profiles"][0]["Guid"] == p["Guid"]
