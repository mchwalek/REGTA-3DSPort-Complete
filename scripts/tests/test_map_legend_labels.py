#!/usr/bin/env python3
"""Regression test for the map-screen legend labels of blip markers.

reLCS labelled every entity blip with LG_38, which is "EightBall" in LCS's
GXT. PS2 DrawLegend (SLES_541.35 0x116760) picks the label from the blip's
colour instead: red entity = Threat, green = Pick up, other = Friend; blue
coord = Friend, other = Destination.

Extracts the real CRadar::GetBlipLegendKey from Radar.cpp, compiles it with
a minimal stub, and checks the mapping for bright and dim colours.
"""
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RADAR_CPP = ROOT / "stories" / "src" / "core" / "Radar.cpp"


def extract(source: str, start_marker: str, end_marker: str) -> str:
    start = source.index(start_marker)
    end = source.index(end_marker, start)
    return source[start:end]


class TestMapLegendLabels(unittest.TestCase):
    def test_blip_labels_follow_ps2_colours(self):
        func = extract(RADAR_CPP.read_text(), "const char *\nCRadar::GetBlipLegendKey", "\nvoid\nCRadar::DrawLegend")
        program = r"""
#include <cassert>
#include <cstring>
typedef unsigned char uint8;
typedef int int32;
struct CRGBA { uint8 r, g, b, a; CRGBA(uint8 r, uint8 g, uint8 b, uint8 a) : r(r), g(g), b(b), a(a) {} };
enum { RADAR_SPRITE_ENTITY_BLIP = -2, RADAR_SPRITE_COORD_BLIP = -1 };
struct CRadar { static const char *GetBlipLegendKey(int32 sprite, const CRGBA &colour); };
""" + func + r"""
static void check(int32 sprite, uint8 r, uint8 g, uint8 b, const char *key)
{
	assert(strcmp(CRadar::GetBlipLegendKey(sprite, CRGBA(r, g, b, 255)), key) == 0);
}
int main()
{
	const int32 E = RADAR_SPRITE_ENTITY_BLIP, C = RADAR_SPRITE_COORD_BLIP;
	check(E, 255, 72, 77, "LG_51");   // red: Threat
	check(E, 127, 0, 0, "LG_51");     // dim red
	check(E, 95, 160, 106, "LG_53");  // green: Pick up
	check(E, 0, 127, 0, "LG_53");     // dim green
	check(E, 72, 77, 255, "LG_52");   // blue: Friend
	check(E, 255, 255, 0, "LG_52");   // any other colour: Friend
	check(C, 72, 77, 255, "LG_52");   // blue coord: Friend
	check(C, 0, 0, 127, "LG_52");     // dim blue coord
	check(C, 255, 72, 77, "LG_35");   // red coord: Destination
	check(C, 255, 255, 0, "LG_35");   // yellow coord: Destination
	return 0;
}
"""
        with tempfile.TemporaryDirectory(prefix="regta-map-legend-test-") as tmp:
            path = Path(tmp) / "test.cpp"
            binary = Path(tmp) / "test"
            path.write_text(program)
            subprocess.run(["c++", "-std=c++11", "-fsanitize=address,undefined", str(path), "-o", str(binary)], check=True)
            subprocess.run([str(binary)], check=True)


if __name__ == "__main__":
    unittest.main()
