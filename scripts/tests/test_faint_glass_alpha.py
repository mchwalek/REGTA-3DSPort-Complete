#!/usr/bin/env python3
"""Regression test: faint glass (no texel alpha >= 128) must be detected.

izzy_dirtGlass (Toni's Portland safehouse windows) has alpha 0..83 only. The
3DS two-pass GS emulation drew it only in its no-depth pass, so later geometry
painted over it. Textures flagged by hasOnlyFaintAlpha are drawn in one
depth-writing pass instead, like PS2 (alpha test off for world geometry).

Extracts the real hasOnlyFaintAlpha/isFaintAlphaSource from 3dsraster.cpp and
etc1Alpha4 from compress.cpp, and compiles them into cpp/faint_glass_alpha.cpp
with minimal stubs.
"""
import unittest

from cpptest import Program, between, harness, read_source


class TestFaintGlassAlpha(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # The hasOnlyFaintAlpha slice runs through isFaintAlphaSource too.
        raster = between(read_source("common/librw/src/3ds/3dsraster.cpp"),
                         "static bool\nhasOnlyFaintAlpha", "\n#define GX_TRANSFER_FMT_NONE")
        assert "static bool\nisFaintAlphaSource" in raster
        alpha4 = between(read_source("common/librw/src/3ds/tex/compress.cpp"),
                         "static uint32_t\netc1Alpha4", "\n  \nvoid\netc1_common")
        cls.program = Program(harness("faint_glass_alpha.cpp", RASTER=raster, ALPHA4=alpha4), sanitize=False)

    @classmethod
    def tearDownClass(cls):
        cls.program.close()

    def _scenario(self, name):
        self.assertEqual(self.program.run(name).strip(), "ok")

    def test_faint_alpha_detection(self):
        self._scenario("faint_alpha_detection")

    def test_faint_alpha_rounds_in_etc1a4(self):
        self._scenario("faint_alpha_rounds_in_etc1a4")


if __name__ == "__main__":
    unittest.main()
