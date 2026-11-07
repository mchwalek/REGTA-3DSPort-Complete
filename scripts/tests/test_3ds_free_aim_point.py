#!/usr/bin/env python3
"""Regression test for the 3DS free-aim point's vertical/yaw update
(Update3DSFreeAimPointAngles in stories/src/core/Cam.cpp).

Extracts the real function body, compiles it into cpp/free_aim_point.cpp
(stub CVector/CGeneral), and asserts the PS2-derived pitch envelope
(50-110 degrees from the ped's vertical, with accept/reject hysteresis) and
yaw cone (+-110 degrees off the ped's forward, same hysteresis pattern).
"""
import unittest

from cpptest import Program, extract_function, harness, read_source


class Test3DSFreeAimPointAngles(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fn = extract_function(read_source("stories/src/core/Cam.cpp"), "static void\nUpdate3DSFreeAimPointAngles(")
        cls.program = Program(harness("free_aim_point.cpp", FUNCTION=fn))

    @classmethod
    def tearDownClass(cls):
        cls.program.close()

    def _scenario(self, name):
        self.assertEqual(self.program.run(name).strip(), "ok")

    def test_full_down_stick_converges_and_stops_at_110(self):
        self._scenario("full_down_stick_converges_and_stops_at_110")

    def test_recovers_from_below_floor_with_hysteresis(self):
        self._scenario("recovers_from_below_floor_with_hysteresis")

    def test_yaw_cone_stops_at_110_and_reenters_on_reverse(self):
        self._scenario("yaw_cone_stops_at_110_and_reenters_on_reverse")

    def test_point_stays_at_range_from_pivot_after_accepted_yaw(self):
        self._scenario("point_stays_at_range_from_pivot_after_accepted_yaw")

    def test_zero_dt_is_a_noop(self):
        self._scenario("zero_dt_is_a_noop")


if __name__ == "__main__":
    unittest.main()
