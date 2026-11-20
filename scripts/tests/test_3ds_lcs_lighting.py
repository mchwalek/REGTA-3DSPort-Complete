#!/usr/bin/env python3
"""LCS applies the PS2 colour filter at full strength (gain = 1 + colour).

III/VC gains are unchanged; fog compensation still cancels the LCS grade.
"""
import unittest

from cpptest import compile_and_run, harness, read_source


class TestLcsLighting(unittest.TestCase):
    def test_colour_gain(self):
        header = read_source("common/3ds/PS2GraphicsProfile.h").replace("#pragma once\n", "")
        self.assertEqual(compile_and_run(harness("lcs_lighting.cpp", PROFILE=header)).strip(), "ok")


if __name__ == "__main__":
    unittest.main()
