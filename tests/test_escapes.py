from livery.escapes import (
    default_look, reset, reset_tab_color, set_profile, tab_color, title,
)


def test_set_profile():
    assert set_profile("livery: x") == "\033]1337;SetProfile=livery: x\007"


def test_tab_color_three_channels():
    assert tab_color((10, 20, 30)) == ("\033]6;1;bg;red;brightness;10\007"
                                       "\033]6;1;bg;green;brightness;20\007"
                                       "\033]6;1;bg;blue;brightness;30\007")


def test_title():
    assert title("Slowboard | dev") == "\033]0;Slowboard | dev\007"


def test_reset_tab_color():
    assert reset_tab_color() == "\033]6;1;bg;*;default\007"


def test_default_look():
    assert default_look() == "\033]1337;SetProfile=Default\007\033]6;1;bg;*;default\007"


def test_reset_clears_title_then_default_look():
    assert reset() == "\033]0;\007\033]1337;SetProfile=Default\007\033]6;1;bg;*;default\007"
