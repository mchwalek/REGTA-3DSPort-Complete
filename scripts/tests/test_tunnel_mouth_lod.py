#!/usr/bin/env python3
"""Regression test: the Shoreside tunnel west mouth LOD follows PS2's sectors.

LODl_tunnel1 has a black arch behind its portal facade. The real tunnel is
wider and bends east, so the arch stands inside the drivable tunnel and is in
view from most of its west half. PS2 lists the LOD only in the sectors east
of the bend and fades it with the sector crossfade when the camera crosses
that line. The 3DS renderer dropped it only near the mouth, with no fade.

Extracts the real IsCameraInsideLCSTunnelLod and the sector rule and
crossfade from Renderer.cpp and compiles them into cpp/tunnel_mouth_lod.cpp
and cpp/tunnel_lod_crossfade.cpp.
"""
import unittest

from cpptest import between, compile_and_run, extract_function, harness, read_source


class TestTunnelMouthLod(unittest.TestCase):
    def test_lod_hidden_only_near_its_own_bounds(self):
        func = between(read_source("stories/src/renderer/Renderer.cpp"),
                       "static bool\nIsCameraInsideLCSTunnelLod", "\nstatic float\nGetLCSWorldLodScale")
        compile_and_run(harness("tunnel_mouth_lod.cpp", FUNCTION=func))

    def test_lod_fades_out_west_of_the_tunnel_bend(self):
        func = between(read_source("stories/src/renderer/Renderer.cpp"),
                       "static const float LCS_TUNNEL_CROSSFADE_START", "\nstatic float\nLCSPS2BuildingOpacity")
        compile_and_run(harness("tunnel_lod_crossfade.cpp", FUNCTION=func))

    def test_lod_opacity_uses_the_crossfade(self):
        source = read_source("stories/src/renderer/Renderer.cpp")
        opacity = extract_function(source, "static float\nLCSPS2BuildingOpacity(CEntity *ent)")
        self.assertIn("LCSTunnelLodCrossfadeOpacity(", opacity)
        # Every return must carry the tunnel factor, also with PS2 draw distance off.
        self.assertNotIn("return 1.0f;", opacity)
        construct = extract_function(source, "void\nCRenderer::ConstructRenderList(void)")
        self.assertIn("UpdateLCSTunnelLodCrossfade(ms_vecCameraPosition", construct)
        self.assertLess(construct.index("ms_vecCameraPosition = "),
                        construct.index("UpdateLCSTunnelLodCrossfade("))


if __name__ == "__main__":
    unittest.main()
