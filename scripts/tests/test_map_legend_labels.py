#!/usr/bin/env python3
"""Regression test for the map-screen legend labels of blip markers.

reLCS labelled every entity blip with LG_38, which is "EightBall" in LCS's
GXT. PS2 DrawLegend (SLES_541.35 0x116760) picks the label from the blip's
colour instead: red entity = Threat, green = Pick up, other = Friend; blue
coord = Friend, other = Destination.

Extracts the real CRadar::GetBlipLegendKey from Radar.cpp, compiles it into
cpp/map_legend_labels.cpp, and checks the mapping for bright and dim colours.
"""
import unittest

from cpptest import between, compile_and_run, harness, read_source


class TestMapLegendLabels(unittest.TestCase):
    def test_blip_labels_follow_ps2_colours(self):
        func = between(read_source("stories/src/core/Radar.cpp"),
                       "const char *\nCRadar::GetBlipLegendKey", "\nvoid\nCRadar::DrawLegend")
        compile_and_run(harness("map_legend_labels.cpp", FUNCTION=func))


if __name__ == "__main__":
    unittest.main()
