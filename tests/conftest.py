import os
import struct
import zlib
from pathlib import Path

import pytest

# Geen kunstmatige profiel-laad-pauze tijdens tests.
os.environ.setdefault("LIVERY_PROFILE_DELAY", "0")


def _make_png(path, rgb, w=16, h=16):
    """Schrijf een geldige 8-bit RGB PNG van w×h in één effen kleur."""
    def chunk(typ, data):
        body = typ + data
        return struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body) & 0xFFFFFFFF)

    sig = b"\x89PNG\r\n\x1a\n"
    ihdr = struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)  # 8-bit, color type 2 (RGB)
    row = b"\x00" + (bytes(rgb) * w)                     # filter byte 0 + pixels
    idat = zlib.compress(row * h)
    Path(path).write_bytes(sig + chunk(b"IHDR", ihdr) + chunk(b"IDAT", idat) + chunk(b"IEND", b""))


@pytest.fixture
def make_png():
    return _make_png
