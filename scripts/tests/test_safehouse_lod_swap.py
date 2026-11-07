#!/usr/bin/env python3
"""Regression test: a swapped-out safehouse shell must not leave its LOD drawn.

main.scm swaps ind_land097 (Toni's Portland building) for TonisAptInterior1.
The shell's LOD (LOD_land097) has dark painted window quads just outside the
interior glass; drawn around the interior they look like a black plane. PS2
swaps the whole sector and never draws that LOD there.

Extracts the real IsLCSBuildingLodSourceSwappedOut from Renderer.cpp and
compiles it into cpp/safehouse_lod_swap.cpp.
"""
import unittest

from cpptest import between, compile_and_run, harness, read_source


class TestSafehouseLodSwap(unittest.TestCase):
    def test_lod_hidden_only_for_matching_swapped_building(self):
        func = between(read_source("stories/src/renderer/Renderer.cpp"),
                       "static bool\nIsLCSBuildingLodSourceSwappedOut", "\n// Reuse bounds")
        compile_and_run(harness("safehouse_lod_swap.cpp", FUNCTION=func), sanitize=False)


if __name__ == "__main__":
    unittest.main()
