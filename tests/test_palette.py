from livery import palette


def test_foreground_is_high_contrast_on_orange():
    # De default-tekstkleur moet ruim leesbaar zijn op het oranje (WCAG AA).
    assert palette.contrast_ratio(palette.FOREGROUND, palette.BG) >= 4.5


def test_all_ansi_colors_stay_legible_on_orange():
    # Elke accentkleur moet minstens een legibiliteits-vloer halen op oranje.
    assert len(palette.ANSI) == 16
    for hexcol in palette.ANSI:
        assert palette.contrast_ratio(hexcol, palette.BG) >= 1.8, hexcol


def test_contrast_ratio_symmetric_and_white_on_black_is_21():
    assert round(palette.contrast_ratio("#FFFFFF", "#000000"), 1) == 21.0
    assert palette.contrast_ratio("#FFFFFF", "#000000") == palette.contrast_ratio("#000000", "#FFFFFF")


def test_all_ansi_colors_stay_legible_on_yellow():
    # Het gedeelde donkere palet moet ook werken voor de dev/watch-gele look.
    for hexcol in palette.ANSI:
        assert palette.contrast_ratio(hexcol, "#FFE75D") >= 1.8, hexcol
    assert palette.contrast_ratio(palette.FOREGROUND, "#FFE75D") >= 1.8
