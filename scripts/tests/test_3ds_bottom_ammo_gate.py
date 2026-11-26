#!/usr/bin/env python3
"""Regression test for when the 3DS bottom screen draws the ammo count.

PS2 CHud::Draw (SLES_541.35 0x240570-0x2405d8) draws no ammo text when
Min(9999, total - clip) == 9999, during a rampage, for slots below 2 and for
the detonator. Scripted infinite ammo (ATTACH_CHAR_TO_CAR gives 30000 rounds,
PS2 0x1f0aac) therefore shows no count. The bottom screen printed "9999-100"
for it.

Extracts the real ShouldDrawAmmo3DS from BottomScreen3DS.cpp, compiles it into
cpp/bottom_ammo_gate.cpp and checks each case.
"""
import unittest

from cpptest import Program, extract_function, harness, read_source

SCENARIOS = [
    "normal_reserve_draws",
    "reserve_9998_draws",
    "reserve_9999_hides",
    "attach_30000_hides",
    "empty_clip_30000_hides",
    "rampage_hides",
    "melee_slot_hides",
    "detonator_hides",
]


class Test3DSBottomAmmoGate(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fn = extract_function(read_source("stories/src/core/BottomScreen3DS.cpp"), "static bool\nShouldDrawAmmo3DS(")
        cls.program = Program(harness("bottom_ammo_gate.cpp", FUNCTION=fn))

    @classmethod
    def tearDownClass(cls):
        cls.program.close()

    def test_scenarios(self):
        for name in SCENARIOS:
            with self.subTest(name):
                self.assertEqual(self.program.run(name).strip(), "ok")


if __name__ == "__main__":
    unittest.main()
