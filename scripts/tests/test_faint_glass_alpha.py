#!/usr/bin/env python3
"""Regression test: faint glass (no texel alpha >= 128) must be detected.

izzy_dirtGlass (Toni's Portland safehouse windows) has alpha 0..83 only. The
3DS two-pass GS emulation drew it only in its no-depth pass, so later geometry
painted over it. Textures flagged by hasOnlyFaintAlpha are drawn in one
depth-writing pass instead, like PS2 (alpha test off for world geometry).

Extracts the real hasOnlyFaintAlpha from 3dsraster.cpp and compiles it with
minimal stubs.
"""
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RASTER_CPP = ROOT / "common" / "librw" / "src" / "3ds" / "3dsraster.cpp"


def extract(source: str, start_marker: str, end_marker: str) -> str:
    start = source.index(start_marker)
    end = source.index(end_marker, start)
    return source[start:end]


class TestFaintGlassAlpha(unittest.TestCase):
    def test_faint_alpha_detection(self):
        func = extract(RASTER_CPP.read_text(), "static bool\nhasOnlyFaintAlpha", "\n#define GX_TRANSFER_FMT_NONE")
        program = r"""
#include <cassert>
#include <cstring>
#define nil nullptr
typedef unsigned char uint8;
typedef unsigned int uint32;
enum GPU_TEXCOLOR { GPU_RGBA8, GPU_ETC1A4, GPU_RGB8 };
struct C3DRaster { GPU_TEXCOLOR format; bool hasAlpha; };
""" + func + r"""
int main()
{
	uint8 etc[32];
	C3DRaster etcRas{GPU_ETC1A4, true};
	memset(etc, 0, sizeof(etc));
	assert(!hasOnlyFaintAlpha(&etcRas, etc, sizeof(etc)));  // fully transparent
	etc[3] = 0x45; etc[24] = 0x77;                           // colour bytes ignored
	etc[16 + 2] = 0x57;
	assert(hasOnlyFaintAlpha(&etcRas, etc, sizeof(etc)));
	etc[5] = 0x80;                                           // one texel at 136
	assert(!hasOnlyFaintAlpha(&etcRas, etc, sizeof(etc)));
	etc[5] = 0x08;
	assert(!hasOnlyFaintAlpha(&etcRas, etc, sizeof(etc)));
	C3DRaster noAlpha{GPU_ETC1A4, false};
	etc[5] = 0;
	assert(!hasOnlyFaintAlpha(&noAlpha, etc, sizeof(etc)));
	assert(!hasOnlyFaintAlpha(&etcRas, nil, 0));

	uint8 rgba[8] = {83, 255, 255, 255, 0, 255, 255, 255};  // ABGR
	C3DRaster rgbaRas{GPU_RGBA8, true};
	assert(hasOnlyFaintAlpha(&rgbaRas, rgba, sizeof(rgba)));
	rgba[4] = 128;
	assert(!hasOnlyFaintAlpha(&rgbaRas, rgba, sizeof(rgba)));

	C3DRaster rgbRas{GPU_RGB8, true};
	assert(!hasOnlyFaintAlpha(&rgbRas, rgba, sizeof(rgba)));
	return 0;
}
"""
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "t.cpp"
            exe = Path(tmp) / "t"
            src.write_text(program)
            subprocess.run(["c++", "-std=c++11", str(src), "-o", str(exe)], check=True)
            subprocess.run([str(exe)], check=True)


if __name__ == "__main__":
    unittest.main()
