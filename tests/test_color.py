import struct

from iterm_favicon.color import average_color, dominant_color, read_bmp


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
