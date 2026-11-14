#!/usr/bin/env python3
"""Regression test: timecycle fog starting behind the camera must fog the near scene.

Foggy weather's fog start is ~-266 m at night. The 3DS clamped it to 55% of the
view range, so nearby geometry had no fog and looked black. Apply3DSFogProfile
now passes a negative start through; SilhouetteFogStart keeps the silhouette
ramp in the rear band so near buildings are not turned into silhouettes.
"""
import unittest

from cpptest import compile_and_run, extract_function, harness, read_source


class TestNearFog(unittest.TestCase):
    def test_profile_math(self):
        header = read_source("common/3ds/PS2GraphicsProfile.h").replace("#pragma once\n", "")
        self.assertEqual(compile_and_run(harness("near_fog.cpp", PROFILE=header)).strip(), "ok")

    def test_negative_start_passes_through(self):
        body = extract_function(read_source("stories/src/core/main.cpp"), "Apply3DSFogProfile(float fogStart)")
        self.assertIn("if(fogStart < 0.0f)", body)


if __name__ == "__main__":
    unittest.main()
