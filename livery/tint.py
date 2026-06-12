import subprocess


def detect_theme():
    """'dark' als macOS in dark mode staat, anders 'light'."""
    try:
        r = subprocess.run(
            ["defaults", "read", "-g", "AppleInterfaceStyle"],
            capture_output=True, text=True,
        )
    except OSError:
        return "light"
    return "dark" if r.returncode == 0 and "Dark" in r.stdout else "light"


def mute(color, theme, strength):
    """Blend color richting de thema-achtergrond. strength 1.0 = pure kleur."""
    bg = (0, 0, 0) if theme == "dark" else (255, 255, 255)
    return tuple(round(c * strength + b * (1 - strength)) for c, b in zip(color, bg))
