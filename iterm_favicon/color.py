import os
import struct
import subprocess
import tempfile
from collections import Counter
from pathlib import Path

NEAR = 24  # drempel voor "bijna zwart/wit"


def read_bmp(data):
    """Lees een ongecomprimeerde 24-bit BMP -> lijst (r,g,b), top-down rij-volgorde."""
    pixel_offset = struct.unpack_from("<I", data, 10)[0]
    width = struct.unpack_from("<i", data, 18)[0]
    height = struct.unpack_from("<i", data, 22)[0]
    bpp = struct.unpack_from("<H", data, 28)[0]
    if bpp != 24:
        raise ValueError(f"verwacht 24-bit BMP, kreeg {bpp}")
    bottom_up = height > 0
    h = abs(height)
    row_size = (width * 3 + 3) & ~3
    out = []
    for row in range(h):
        src = (h - 1 - row) if bottom_up else row
        base = pixel_offset + src * row_size
        for x in range(width):
            b = data[base + x * 3]
            g = data[base + x * 3 + 1]
            r = data[base + x * 3 + 2]
            out.append((r, g, b))
    return out


def average_color(pixels):
    n = len(pixels)
    return tuple(sum(p[i] for p in pixels) // n for i in range(3))


def _extreme(p):
    return all(c <= NEAR for c in p) or all(c >= 255 - NEAR for c in p)


def dominant_color(pixels):
    """Meest voorkomende gequantiseerde niet-extreme kleur; anders gemiddelde."""
    candidates = [p for p in pixels if not _extreme(p)]
    if not candidates:
        return average_color(pixels)
    counts = Counter(tuple(c >> 4 for c in p) for p in candidates)
    winner = counts.most_common(1)[0][0]
    members = [p for p in candidates if tuple(c >> 4 for c in p) == winner]
    return average_color(members)


DOMINANT_SIZE = 16


def sips_pixels(png_path, size):
    """Schaal de PNG naar size×size via sips, lever BMP-pixels (r,g,b)."""
    with tempfile.TemporaryDirectory() as td:
        out = os.path.join(td, "o.bmp")
        subprocess.run(
            ["sips", "-s", "format", "bmp", "-z", str(size), str(size),
             str(png_path), "--out", out],
            check=True, capture_output=True,
        )
        return read_bmp(Path(out).read_bytes())


def color_from_png(png_path):
    """Dominante kleur van een PNG; valt terug op None bij sips/decode-fout."""
    try:
        pixels = sips_pixels(png_path, DOMINANT_SIZE)
    except (subprocess.CalledProcessError, ValueError, OSError):
        return None
    return dominant_color(pixels)
