import struct

from livery.color import average_color, dominant_color, read_bmp


def _bmp(pixels, w, h):
    """Bouw een minimale 24-bit BMP. pixels = lijst van (r,g,b), rij-voor-rij top-down."""
    row_size = (w * 3 + 3) & ~3
    pad = row_size - w * 3
    pixel_data = b""
    for row in range(h - 1, -1, -1):  # BMP is bottom-up
        for x in range(w):
            r, g, b = pixels[row * w + x]
            pixel_data += bytes((b, g, r))
        pixel_data += b"\x00" * pad
    offset = 54
    header = b"BM" + struct.pack("<IHHI", offset + len(pixel_data), 0, 0, offset)
    info = struct.pack("<IiiHHIIiiII", 40, w, h, 1, 24, 0, len(pixel_data), 2835, 2835, 0, 0)
    return header + info + pixel_data


def test_read_bmp_roundtrip():
    pixels = [(255, 0, 0), (0, 255, 0), (0, 0, 255), (10, 20, 30)]
    assert read_bmp(_bmp(pixels, 2, 2)) == pixels


def test_average_color():
    assert average_color([(0, 0, 0), (100, 200, 50)]) == (50, 100, 25)


def test_dominant_ignores_white_and_black():
    # 6 witte, 6 zwarte, 4 blauwe pixels -> dominant moet blauw zijn
    pixels = [(255, 255, 255)] * 6 + [(0, 0, 0)] * 6 + [(20, 40, 200)] * 4
    assert dominant_color(pixels) == (20, 40, 200)


def test_dominant_falls_back_to_average_when_all_extreme():
    pixels = [(255, 255, 255)] * 4 + [(0, 0, 0)] * 4
    # alles is extreem -> gemiddelde
    assert dominant_color(pixels) == average_color(pixels)


import shutil

import pytest

from livery.color import sips_pixels, color_from_png


sips_available = pytest.mark.skipif(shutil.which("sips") is None, reason="sips ontbreekt")


@sips_available
def test_sips_pixels_solid_red(make_png, tmp_path):
    png = tmp_path / "red.png"
    make_png(png, (220, 30, 40), w=32, h=32)
    pixels = sips_pixels(png, 8)
    assert len(pixels) == 64
    r, g, b = pixels[0]
    assert r > 150 and g < 90 and b < 90  # ruwweg rood na herschaling


@sips_available
def test_color_from_png_solid(make_png, tmp_path):
    png = tmp_path / "blue.png"
    make_png(png, (30, 60, 210), w=32, h=32)
    r, g, b = color_from_png(png)
    assert b > 150 and b > r and b > g
