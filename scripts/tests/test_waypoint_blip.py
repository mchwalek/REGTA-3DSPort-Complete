#!/usr/bin/env python3
"""Regression test for the map waypoint blip look.

reLCS created the waypoint as a dim grey height-shaped coord blip. PS2
(SLES_541.35 0x119120) uses a bright red mp_objective sprite (hollow square)
with scale 1.

Extracts the real CRadar::ToggleTargetMarker from Radar.cpp, compiles it into
cpp/waypoint_blip.cpp, and checks the stored blip fields.
"""
import unittest

from cpptest import between, compile_and_run, harness, read_source


class TestWaypointBlip(unittest.TestCase):
    def test_waypoint_matches_ps2(self):
        func = between(read_source("stories/src/core/Radar.cpp"), "void\nCRadar::ToggleTargetMarker", "\n#endif")
        compile_and_run(harness("waypoint_blip.cpp", FUNCTION=func))


if __name__ == "__main__":
    unittest.main()
