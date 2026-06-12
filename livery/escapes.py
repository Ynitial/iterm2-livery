ESC = "\033"
BEL = "\007"


def set_profile(name):
    return f"{ESC}]1337;SetProfile={name}{BEL}"


def tab_color(rgb):
    r, g, b = rgb
    return (f"{ESC}]6;1;bg;red;brightness;{r}{BEL}"
            f"{ESC}]6;1;bg;green;brightness;{g}{BEL}"
            f"{ESC}]6;1;bg;blue;brightness;{b}{BEL}")


def reset_tab_color():
    return f"{ESC}]6;1;bg;*;default{BEL}"


def title(text):
    return f"{ESC}]0;{text}{BEL}"


def default_look():
    """Default-profiel + standaard tabkleur (titel onaangeroerd)."""
    return set_profile("Default") + reset_tab_color()


def reset():
    """Volledige reset voor een niet-themed map: titel wissen + default look."""
    return title("") + default_look()
