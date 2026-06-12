import json

from livery.profile import (
    build_profile, profile_file, profile_guid, profile_name, write_profile,
)


def test_profile_name_uses_root_basename():
    assert profile_name("/Users/yoni/projects/slowboard") == "livery: slowboard"


def test_guid_stable_per_root():
    assert profile_guid("/x") == profile_guid("/x")
    assert profile_guid("/x") != profile_guid("/y")


def test_build_profile_has_icon_and_colors():
    p = build_profile("/x/proj", "/x/proj/a.png", (255, 0, 0), (10, 10, 10))
    assert p["Icon"] == 2
    assert p["Custom Icon Path"] == "/x/proj/a.png"
    assert p["Use Tab Color"] is True
    assert p["Dynamic Profile Parent Name"] == "Default"
    assert abs(p["Tab Color"]["Red Component"] - 1.0) < 1e-6
    assert abs(p["Background Color"]["Red Component"] - 10 / 255) < 1e-6


def test_write_profile_wraps_in_profiles_array(tmp_path):
    p = build_profile("/x/proj", "/x/proj/a.png", (1, 2, 3), (4, 5, 6))
    write_profile(tmp_path, p)
    written = json.loads(profile_file(tmp_path, "/x/proj").read_text())
    assert written["Profiles"][0]["Guid"] == p["Guid"]
