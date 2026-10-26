#!/usr/bin/env python3
"""Regression test for the map waypoint blip look.

reLCS created the waypoint as a dim grey height-shaped coord blip. PS2
(SLES_541.35 0x119120) uses a bright red mp_objective sprite (hollow square)
with scale 1.

Extracts the real CRadar::ToggleTargetMarker from Radar.cpp, compiles it with
a minimal stub, and checks the stored blip fields.
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


class TestWaypointBlip(unittest.TestCase):
    def test_waypoint_matches_ps2(self):
        func = extract(RADAR_CPP.read_text(), "void\nCRadar::ToggleTargetMarker", "\n#endif")
        program = r"""
#include <cassert>
typedef int int32;
typedef short int16;
typedef unsigned short uint16;
typedef unsigned int uint32;
struct CVector { float x, y, z; CVector() {} CVector(float x, float y, float z) : x(x), y(y), z(z) {} };
enum { NUMRADARBLIPS = 75 };
enum { BLIP_NONE, BLIP_CAR, BLIP_CHAR, BLIP_OBJECT, BLIP_COORD };
enum { BLIP_DISPLAY_NEITHER, BLIP_DISPLAY_MARKER_ONLY, BLIP_DISPLAY_BLIP_ONLY, BLIP_DISPLAY_BOTH };
enum { RADAR_TRACE_RED, RADAR_TRACE_GREEN, RADAR_TRACE_LIGHT_BLUE, RADAR_TRACE_GRAY };
enum { RADAR_SPRITE_NONE = 0, RADAR_SPRITE_MPOBJECTIVE = 49 };
struct sRadarTrace {
	uint32 m_nColor; uint32 m_eBlipType; int32 m_nEntityHandle; CVector m_vec2DPos; CVector m_vecPos;
	uint16 m_BlipIndex; bool m_bDim; bool m_bInUse; bool m_bShortRange; bool m_unused; float m_Radius;
	int16 m_wScale; uint16 m_eBlipDisplay; uint16 m_eRadarSprite;
};
struct CRadar {
	static sRadarTrace ms_RadarTrace[NUMRADARBLIPS];
	static int TargetMarkerId;
	static CVector TargetMarkerPos;
	static void ToggleTargetMarker(float, float);
	static int32 GetNewUniqueBlipIndex(int32 i) { return i; }
	static void ClearBlip(int32 i) { ms_RadarTrace[i].m_bInUse = false; }
};
sRadarTrace CRadar::ms_RadarTrace[NUMRADARBLIPS];
int CRadar::TargetMarkerId = -1;
CVector CRadar::TargetMarkerPos;
""" + func + r"""
int main()
{
	CRadar::ToggleTargetMarker(10.0f, 20.0f);
	assert(CRadar::TargetMarkerId >= 0);
	const sRadarTrace &t = CRadar::ms_RadarTrace[CRadar::TargetMarkerId];
	assert(t.m_bInUse && t.m_eBlipType == BLIP_COORD);
	assert(t.m_nColor == RADAR_TRACE_RED && t.m_bDim == 1);
	assert(t.m_eRadarSprite == RADAR_SPRITE_MPOBJECTIVE);
	assert(t.m_wScale == 1 && t.m_eBlipDisplay == BLIP_DISPLAY_BLIP_ONLY);
	assert(t.m_vecPos.x == 10.0f && t.m_vecPos.y == 20.0f && t.m_vecPos.z == 0.0f);
	CRadar::ToggleTargetMarker(0.0f, 0.0f);
	assert(CRadar::TargetMarkerId == -1);
	return 0;
}
"""
        with tempfile.TemporaryDirectory(prefix="regta-waypoint-test-") as tmp:
            path = Path(tmp) / "test.cpp"
            binary = Path(tmp) / "test"
            path.write_text(program)
            subprocess.run(["c++", "-std=c++11", "-fsanitize=address,undefined", str(path), "-o", str(binary)], check=True)
            subprocess.run([str(binary)], check=True)


if __name__ == "__main__":
    unittest.main()
