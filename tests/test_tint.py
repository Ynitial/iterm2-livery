from iterm_favicon.tint import mute


def test_mute_dark_blends_to_black():
    # 50% van (200,100,50) richting zwart
    assert mute((200, 100, 50), "dark", 0.5) == (100, 50, 25)


def test_mute_light_blends_to_white():
    # 0% kleur -> volledig wit
    assert mute((10, 20, 30), "light", 0.0) == (255, 255, 255)


def test_mute_full_strength_is_color():
    assert mute((10, 20, 30), "dark", 1.0) == (10, 20, 30)
