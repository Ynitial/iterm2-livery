import os
import struct
import subprocess
import tempfile
from collections import Counter
from pathlib import Path

NEAR = 24       # drempel voor "bijna zwart/wit"
ALPHA_MIN = 8   # pixels transparanter dan dit tellen niet mee (32-bit BMP)


def read_bmp(data):
    """Lees een ongecomprimeerde 24- of 32-bit BMP -> lijst (r,g,b), top-down.

    Bij 32-bit (BGRA, zoals sips levert voor PNG's met alpha) worden (vrijwel)
    transparante pixels overgeslagen, zodat alleen het zichtbare logo meetelt.
    """
    pixel_offset = struct.unpack_from("<I", data, 10)[0]
    width = struct.unpack_from("<i", data, 18)[0]
    height = struct.unpack_from("<i", data, 22)[0]
    bpp = struct.unpack_from("<H", data, 28)[0]
    if bpp not in (24, 32):
        raise ValueError(f"verwacht 24- of 32-bit BMP, kreeg {bpp}")
    px = bpp // 8
    bottom_up = height > 0
    h = abs(height)
    row_size = (width * px + 3) & ~3
    out = []
    for row in range(h):
        src = (h - 1 - row) if bottom_up else row
        base = pixel_offset + src * row_size
        for x in range(width):
            off = base + x * px
            if px == 4 and data[off + 3] < ALPHA_MIN:
                continue  # transparant -> overslaan
            out.append((data[off + 2], data[off + 1], data[off]))  # B,G,R -> R,G,B
    return out


def average_color(pixels):
    n = len(pixels)
    return tuple(sum(p[i] for p in pixels) // n for i in range(3))


def _extreme(p):
    return all(c <= NEAR for c in p) or all(c >= 255 - NEAR for c in p)


def _saturation(p):
    mx = max(p)
    return 0.0 if mx == 0 else (mx - min(p)) / mx


def _bucket(p):
    return tuple(c >> 4 for c in p)


def dominant_color(pixels):
    """De merkkleur: verzadigingsgewogen meest voorkomende niet-extreme kleur.

    Door op frequentie × verzadiging te wegen wint een levendige accentkleur
    (bv. een rood logo-detail) van een grotere doffe/grijze massa. Heeft het
    icoon geen verzadiging (echt grijs), dan valt het terug op pure frequentie;
    is alles extreem (wit/zwart), dan op het gemiddelde.
    """
    candidates = [p for p in pixels if not _extreme(p)]
    if not candidates:
        return average_color(pixels)
    weighted = Counter()
    for p in candidates:
        weighted[_bucket(p)] += _saturation(p)
    bucket, weight = weighted.most_common(1)[0]
    if weight == 0:  # egaal/grijs icoon -> terug naar frequentie
        bucket = Counter(_bucket(p) for p in candidates).most_common(1)[0][0]
    members = [p for p in candidates if _bucket(p) == bucket]
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
    if not pixels:  # volledig transparant icoon
        return None
    return dominant_color(pixels)
