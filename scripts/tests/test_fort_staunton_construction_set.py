#!/usr/bin/env python3
"""Regression test: the Fort Staunton subway construction set (model ids
3653..3660: Siu_Beam1/2/3, Slab_00, Ramp00, Over_hang, Rubble3, FS_Train)
must stay in the world while the fort is intact.

PS2 keeps these 124 commer.ipl instances in its static building table
(GAME.BIN) and draws them as unswapped LVZ instances in both fort phases.
reLCS deleted them while the fort was intact, so in "Bringing the House Down"
(DONH5) the subway tube had no end caps (Rubble3) and the player could drive
out of the map.

Extracts the real SyncLCSFortStauntonWorld from Script9.cpp and compiles it
into cpp/fort_staunton_world.cpp.
"""
import unittest

from cpptest import compile_and_run, extract_function, harness, read_source


class TestFortStauntonConstructionSet(unittest.TestCase):
    def test_construction_set_survives_both_phases(self):
        func = extract_function(read_source("stories/src/control/Script9.cpp"),
                                "void\nSyncLCSFortStauntonWorld(void)")
        compile_and_run(harness("fort_staunton_world.cpp", FUNCTION=func))


if __name__ == "__main__":
    unittest.main()
