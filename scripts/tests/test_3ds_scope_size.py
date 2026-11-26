#!/usr/bin/env python3
"""Regression test for the 3DS sniper / laser scope size (PS2 LCS behaviour,
SLES_541.35 0x23f540): PS2 draws the four scope quadrants with a half-extent
of 210 x 210 PSP units (480x272 HUD space), so the circle fills the screen
height, and PS2 has no black frame around the rocket launcher sight.

Extracts the real GetPS2ScopeRect3DS from Hud.cpp, compiles it into
cpp/scope_size.cpp and checks that:
- the half-extent is 210 * 240/272 px on both axes, centred on 400x240,
- the rect covers the full screen height and stays inside the screen width.

Also checks that Render2dStuff (main.cpp) compiles VC's sniper/rocket
borders out on _3DS, because they would paint over the bigger scope.
"""
import unittest

from cpptest import between, compile_and_run, extract_function, harness, read_source


class Test3DSScopeSize(unittest.TestCase):
    def test_scope_rect_matches_ps2(self):
        hud = read_source("stories/src/renderer/Hud.cpp")
        helper = extract_function(hud, "static CRect\nGetPS2ScopeRect3DS")
        compile_and_run(harness("scope_size.cpp", HELPER=helper))

    def test_render2dstuff_borders_not_on_3ds(self):
        main = read_source("stories/src/core/main.cpp")
        block = between(main, "TheCamera.DrawBordersForWideScreen();", "MusicManager.DisplayRadioStationName();")
        self.assertIn("// Draw black border for sniper and rocket launcher", block)
        guarded = between(block, "#ifndef _3DS", "#endif")
        self.assertIn("// Draw black border for sniper and rocket launcher", guarded)
        self.assertIn("SCREEN_SCALE_X(210)", guarded)


if __name__ == "__main__":
    unittest.main()
