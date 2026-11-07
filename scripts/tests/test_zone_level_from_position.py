#!/usr/bin/env python3
"""CTheZones::GetLevelFromPosition must match PS2 (SLES_541.35 0x2d3b20).

reLCS used to return the first containing map zone's level. Portland and
Staunton zones overlap across the channel, so a boat ("Caught In The Act")
flipped CTheZones::m_CurrLevel back and forth and every flip ran the
blocking island swap with its load screen. PS2 keeps the current level
while any containing zone has it.

The scenarios live in cpp/zone_level_from_position.cpp.
"""
import unittest

from cpptest import Program, extract_function, harness, read_source


class ZoneLevelFromPosition(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fn = extract_function(read_source("stories/src/core/Zones.cpp"), "eLevelName\nCTheZones::GetLevelFromPosition")
        cls.program = Program(harness("zone_level_from_position.cpp", FUNCTION=fn))

    @classmethod
    def tearDownClass(cls):
        cls.program.close()

    def _scenario(self, name):
        self.assertEqual(self.program.run(name).strip(), "ok")

    def test_overlap_keeps_current_level(self):
        self._scenario("overlap_keeps_current_level")

    def test_overlap_from_elsewhere_takes_last_match(self):
        self._scenario("overlap_from_elsewhere_takes_last_match")

    def test_underground_only_counts_if_first_or_current(self):
        self._scenario("underground_only_counts_if_first_or_current")

    def test_no_zone_is_generic(self):
        self._scenario("no_zone_is_generic")


if __name__ == "__main__":
    unittest.main()
