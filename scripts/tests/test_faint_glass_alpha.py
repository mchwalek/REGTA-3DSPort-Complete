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
COMPRESS_CPP = ROOT / "common" / "librw" / "src" / "3ds" / "tex" / "compress.cpp"


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

    def test_faint_alpha_rounds_in_etc1a4(self):
        source = RASTER_CPP.read_text()
        faint = extract(source, "static bool\nisFaintAlphaSource", "\n#define GX_TRANSFER_FMT_NONE")
        alpha4 = extract(COMPRESS_CPP.read_text(), "static uint32_t\netc1Alpha4", "\n  \nvoid\netc1_common")
        program = r"""
#include <cassert>
#include <cstdint>
typedef unsigned char uint8;
typedef unsigned int uint32;
""" + faint + alpha4 + r"""
int main()
{
	// izzy_dirtGlass alphas: flooring zeroed 3, 9, 11; rounding keeps 9 and 11.
	assert(etc1Alpha4(9, false) == 0 && etc1Alpha4(9, true) == 1);
	assert(etc1Alpha4(43, false) == 2 && etc1Alpha4(43, true) == 3);
	assert(etc1Alpha4(3, true) == 0 && etc1Alpha4(83, true) == 5);
	assert(etc1Alpha4(127, true) == 7);                      // stays below the faint limit
	assert(etc1Alpha4(255, true) == 15 && etc1Alpha4(255, false) == 15);

	uint8 px[2*12] = {};                                     // 2x2 RGBA, stride 12
	assert(!isFaintAlphaSource(px, 2, 2, 12));               // fully transparent
	px[3] = 83; px[11] = 200;                                // padding ignored
	assert(isFaintAlphaSource(px, 2, 2, 12));
	px[12 + 7] = 128;
	assert(!isFaintAlphaSource(px, 2, 2, 12));
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
