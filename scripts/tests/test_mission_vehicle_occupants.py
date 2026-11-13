#!/usr/bin/env python3
"""Regression test: occupants of mission vehicles stay visible past vehicle LOD0.

Trello "[Calm Before the Storm] Massimo's model disappears in the cutscene
with Diablos": Massimo sits in the mission maverick ~20-25 m from the script
camera. reLCS's _3DS RenderOneNonRoad hid occupants beyond the big-vehicle
LOD0 distance; PS2 has no such gate (only CPed::Render's 25 m in-car cull,
0x1e2458), so mission vehicles must bypass it.
"""
import unittest

from cpptest import between, compile_and_run, harness, read_source, strip_comments


class TestMissionVehicleOccupants(unittest.TestCase):
    def test_mission_vehicle_occupants_skip_lod_gate(self):
        source = read_source("stories/src/renderer/Renderer.cpp")
        gate = between(source, "renderOccupants = vehicleClump &&", ";", include_end=True)
        compile_and_run(harness("mission_vehicle_occupants.cpp", GATE=strip_comments(gate)))


if __name__ == "__main__":
    unittest.main()
