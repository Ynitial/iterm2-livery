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


def bg_color(hexcol):
    """Zet de achtergrondkleur van deze sessie (OSC 11), zonder profielwissel."""
    return f"{ESC}]11;{hexcol}{BEL}"


def fg_color(hexcol):
    """Zet de voorgrond-/tekstkleur van deze sessie (OSC 10)."""
    return f"{ESC}]10;{hexcol}{BEL}"


def ansi_color(index, hexcol):
    """Zet één van de 16 ANSI-paletkleuren (OSC 4)."""
    return f"{ESC}]4;{index};{hexcol}{BEL}"


def reset_colors():
    """Herstel achtergrond/voorgrond/palet naar de profiel-defaults (OSC 111/110/104)."""
    return f"{ESC}]111{BEL}{ESC}]110{BEL}{ESC}]104{BEL}"


def default_look():
    """Default-profiel + standaard tabkleur (titel onaangeroerd)."""
    return set_profile("Default") + reset_tab_color()


def reset():
    """Volledige reset voor een niet-themed map: titel wissen + default look."""
    return title("") + default_look()
