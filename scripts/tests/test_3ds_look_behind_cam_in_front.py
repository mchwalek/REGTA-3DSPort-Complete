#!/usr/bin/env python3
"""Regression test for the 3DS in-car look-behind (LookBehindCamIsInFront3DS
in stories/src/core/Cam.cpp).

CCam::LookBehind decides whether the camera was in front of the car from
geometry, so it works for both Beta conventions (string cam and
Process_FollowCar_SA). Process_FollowCar_SA therefore no longer flips its
own Beta for look-behind, which left SourceBeforeLookBehind in front of the
car and turned the radar 180 degrees.
"""
import unittest

from cpptest import Program, extract_function, harness, read_source


class Test3DSLookBehindCamInFront(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = read_source("stories/src/core/Cam.cpp")
        fn = extract_function(cls.source, "static bool\nLookBehindCamIsInFront3DS(")
        cls.program = Program(harness("look_behind_cam_in_front.cpp", FUNCTION=fn))

    @classmethod
    def tearDownClass(cls):
        cls.program.close()

    def _scenario(self, name):
        self.assertEqual(self.program.run(name).strip(), "ok")

    def test_chase_cam_behind_car_is_not_in_front(self):
        self._scenario("chase_cam_behind_car_is_not_in_front")

    def test_cam_ahead_of_car_is_in_front(self):
        self._scenario("cam_ahead_of_car_is_in_front")

    def test_follow_car_sa_does_not_flip_beta_on_3ds(self):
        sa = extract_function(self.source, "void\nCCam::Process_FollowCar_SA(")
        flip = sa.index("TheCamera.m_bCamDirectlyInFront = true;")
        nearest_directive = sa[:flip].rsplit("\n#", 1)[1]
        self.assertTrue(nearest_directive.startswith("ifndef _3DS"))


if __name__ == "__main__":
    unittest.main()
