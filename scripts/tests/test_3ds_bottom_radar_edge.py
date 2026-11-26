#!/usr/bin/env python3
"""Regression test for remote blips on the 3DS bottom-screen radar.

The bottom radar fills the 320x240 screen, a rectangle. LimitRadarPoint used
PS2's unit-circle test (SLES_541.35 0x1188e0) there: blips in the corners that
were on screen got pushed out to the edge, and short-range blips there were
hidden. LimitBottomRadarPoint3DS in stories/src/core/Radar.cpp now measures
against the inset rectangle (1.0 = edge, like PS2's circle radius).

Extracts the real helper, compiles it into cpp/bottom_radar_edge.cpp and checks
that points inside the rectangle stay put, points outside land on its edge in
the same direction, and the returned measure is linear with 1.0 on the edge.
"""
import unittest

from cpptest import Program, extract_function, harness, read_source


class Test3DSBottomRadarEdge(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fn = extract_function(read_source("stories/src/core/Radar.cpp"), "static float\nLimitBottomRadarPoint3DS(")
        cls.program = Program(harness("bottom_radar_edge.cpp", FUNCTION=fn))

    @classmethod
    def tearDownClass(cls):
        cls.program.close()

    def _scenario(self, name):
        self.assertEqual(self.program.run(name).strip(), "ok")

    def test_corner_inside_rectangle_stays_put(self):
        self._scenario("corner_inside")

    def test_point_under_status_rail_stays_put(self):
        self._scenario("under_rail")

    def test_far_points_land_on_edge_in_same_direction(self):
        self._scenario("far_points")

    def test_point_on_edge_measures_one(self):
        self._scenario("on_edge")

    def test_measure_is_linear(self):
        self._scenario("linear")

    def test_origin(self):
        self._scenario("origin")

    def test_north_marker_distance_is_always_outside(self):
        self._scenario("north_distance")


if __name__ == "__main__":
    unittest.main()
