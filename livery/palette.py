"""Kleuren voor de Claude-modus: een oranje achtergrond met een donker,
leesbaar ANSI-palet (donkere tekst op oranje = een 'light'-achtige look)."""

BG = "#D97757"          # referentie-oranje voor de contrast-vloer van het palet
FOREGROUND = "#2B1810"  # donkere tekst voor LICHTE achtergronden (oranje/geel)
FOREGROUND_ON_DARK = "#F3E7E0"  # lichte tekst voor DONKERE achtergronden (bv. #57392F)

# Onder deze luminantie is een achtergrond "donker" en gebruiken we lichte tekst.
_DARK_BG_THRESHOLD = 0.18

# 16 ANSI-kleuren, bewust donker/verzadigd zodat álle tekst leesbaar blijft op
# het oranje; onderscheid zit in de tint, niet in de helderheid.
ANSI = [
    "#211A16",  # 0  zwart
    "#7A1F12",  # 1  rood
    "#2F5A22",  # 2  groen
    "#6B4A12",  # 3  geel
    "#243D66",  # 4  blauw
    "#5C2450",  # 5  magenta
    "#1E534F",  # 6  cyaan
    "#3A2E26",  # 7  'wit' (donker gehouden voor leesbaarheid)
    "#3A302A",  # 8  fel zwart
    "#8E2E1C",  # 9  fel rood
    "#356423",  # 10 fel groen
    "#6E4E18",  # 11 fel geel
    "#2E4C7E",  # 12 fel blauw
    "#6E2E60",  # 13 fel magenta
    "#286460",  # 14 fel cyaan
    "#4A3C30",  # 15 fel wit (donker gehouden)
]


def _rgb(hexcol):
    h = hexcol.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def _luminance(hexcol):
    def chan(c):
        c /= 255
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (chan(c) for c in _rgb(hexcol))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast_ratio(hex_a, hex_b):
    """WCAG-contrastverhouding (1.0–21.0) tussen twee hex-kleuren."""
    la, lb = _luminance(hex_a), _luminance(hex_b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


def is_dark(bg_hex):
    """True als de achtergrond donker genoeg is om lichte tekst te vragen."""
    return _luminance(bg_hex) < _DARK_BG_THRESHOLD


def foreground_for(bg_hex):
    """Kies leesbare voorgrondkleur bij een achtergrond: licht op donker,
    donker op licht."""
    return FOREGROUND_ON_DARK if is_dark(bg_hex) else FOREGROUND
