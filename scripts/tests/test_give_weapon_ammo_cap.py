#!/usr/bin/env python3
"""Regression test: CPed::GiveWeapon (stories/src/peds/Ped.cpp) must clamp a
new ammo total in 10000..29999 to 9999, like PS2 0x1e1180. Without the clamp,
the Scooter Shooter ammo doubling (original game behaviour) passes 9999, the
HUD hides the count, and the SMG looks like it has infinite ammo."""
import unittest

from cpptest import Program, extract_function, harness, read_source


class TestGiveWeaponAmmoCap(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        src = read_source("stories/src/peds/Ped.cpp")
        clamp = extract_function(src, "static uint32\nClampFiniteAmmo(")
        give = extract_function(src, "int32\nCPed::GiveWeapon(eWeaponType weaponType")
        cls.program = Program(harness("give_weapon_ammo_cap.cpp", GIVE_WEAPON=clamp + give))

    @classmethod
    def tearDownClass(cls):
        cls.program.close()

    def _scenario(self, name):
        self.assertEqual(self.program.run(name).strip(), "ok")

    def test_same_type_total_clamped_to_9999(self):
        self._scenario("same_type_clamped")

    def test_same_type_infinite_amount_kept(self):
        self._scenario("same_type_infinite_kept")

    def test_merged_slot_total_clamped_to_9999(self):
        self._scenario("merged_slot_clamped")

    def test_unmerged_slot_replaces_ammo(self):
        self._scenario("unmerged_slot_replaced")

    def test_empty_slot_keeps_given_amount(self):
        self._scenario("empty_slot_kept")

    def test_scooter_shooter_doubling_stops_at_9999(self):
        self._scenario("scooter_shooter_doubling_stops_at_9999")


if __name__ == "__main__":
    unittest.main()
