#!/usr/bin/env python3
"""Regression test: the Shoreside tunnel west mouth LOD is hidden from inside.

LODl_tunnel1 has a black arch behind its portal facade. The real tunnel is
wider and bends east, so the arch stands inside the drivable tunnel. The 3DS
renderer hid the LOD only when the detailed portal was on screen, so it drew
whenever the player looked into the tunnel. PS2 lists the LOD in no sector
near the mouth.

Extracts the real IsCameraInsideLCSTunnelLod from Renderer.cpp and compiles
it into cpp/tunnel_mouth_lod.cpp.
"""
import unittest

from cpptest import between, compile_and_run, harness, read_source


class TestTunnelMouthLod(unittest.TestCase):
    def test_lod_hidden_only_near_its_own_bounds(self):
        func = between(read_source("stories/src/renderer/Renderer.cpp"),
                       "static bool\nIsCameraInsideLCSTunnelLod", "\nstatic float\nGetLCSWorldLodScale")
        compile_and_run(harness("tunnel_mouth_lod.cpp", FUNCTION=func))


if __name__ == "__main__":
    unittest.main()
