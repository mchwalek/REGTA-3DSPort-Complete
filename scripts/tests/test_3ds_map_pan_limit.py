#!/usr/bin/env python3
"""Regression test for the 3DS pause-menu map panning (PS2 LCS behaviour,
SLES_541.35 0x33f578): the map scrolls under a centred crosshair until its
edge (the 320x220 atlas, see CMenuManager::PrintMap) meets the screen edge,
then the crosshair itself moves. Moving back snaps the crosshair to the
centre before the map scrolls again.

Extracts the real MAP_PAN_LIMIT_X/_Y macros and screen<->world helpers from
Frontend.cpp, includes common/3ds/MapPan3DS.h, compiles against a minimal
stub and checks that:
- every atlas corner is reachable by the crosshair at min and max zoom,
- the crosshair stays centred while the map can still scroll,
- moving back snaps the crosshair to the centre,
- MapScreenToWorld3DS and MapWorldToScreen3DS are inverses.
"""
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FRONTEND_CPP = ROOT / "stories" / "src" / "core" / "Frontend.cpp"
RADAR_H = ROOT / "stories" / "src" / "core" / "Radar.h"
MAP_PAN_H = ROOT / "common" / "3ds" / "MapPan3DS.h"


def extract(source: str, start_marker: str, end_marker: str) -> str:
    start = source.index(start_marker)
    end = source.index(end_marker, start)
    return source[start:end]


def build_and_run(cpp_source: str) -> None:
    with tempfile.TemporaryDirectory(prefix="regta-map-pan-limit-test-") as tmp:
        path = Path(tmp) / "test_map_pan_limit.cpp"
        binary = Path(tmp) / "test_map_pan_limit"
        path.write_text(cpp_source)
        subprocess.run(
            ["c++", "-std=c++11", "-fsanitize=address,undefined",
             str(path), "-o", str(binary)],
            check=True,
        )
        subprocess.run([str(binary)], check=True)


class Test3DSMapPanLimit(unittest.TestCase):
    def test_ps2_map_pan(self):
        frontend = FRONTEND_CPP.read_text()
        macros = extract(frontend, "#define MAP_PAN_LIMIT_X(s) Max", "#define CAN_PAN_X_AT_CURRENT_ZOOM")
        helpers = extract(frontend, "static CVector2D\nMapScreenToWorld3DS", "#endif\n\n#ifdef CUTSCENE_BORDERS_SWITCH")
        registration = "".join(line + "\n" for line in RADAR_H.read_text().splitlines()
                               if line.startswith("#define LCS_MENU_MAP_"))

        stub = r"""
#include <cassert>
#include <cmath>
#include <cstdio>

#define _3DS
#include """ + '"' + str(MAP_PAN_H) + '"' + r"""
static float Max(float a, float b) { return a > b ? a : b; }
#define SCREEN_WIDTH 400.0f
#define SCREEN_HEIGHT 240.0f
#define MENU_Y(y) ((y) * SCREEN_HEIGHT / 448.0f)
struct CVector2D { float x, y; CVector2D(float x, float y) : x(x), y(y) {} };
""" + registration + macros + helpers + r"""

struct Map { float size, cx, cy, ox, oy; };

static void pan(Map &m, float dx, float dy) {
	MapPan3DS::Pan(dx, m.ox, m.cx, SCREEN_WIDTH / 2, MAP_PAN_LIMIT_X(m.size), SCREEN_WIDTH / 2);
	MapPan3DS::Pan(dy, m.oy, m.cy, SCREEN_HEIGHT / 2, MAP_PAN_LIMIT_Y(m.size), SCREEN_HEIGHT / 2);
}

// Crosshair position in atlas pixels (0..320, 0..220).
static void atlas(const Map &m, float &ax, float &ay) {
	const float scale = m.size * 2.0f / 220.0f;
	ax = (SCREEN_WIDTH / 2 + m.ox - (m.cx - m.size * (320.0f / 220.0f))) / scale;
	ay = (SCREEN_HEIGHT / 2 + m.oy - (m.cy - m.size)) / scale;
}

int main() {
	float sizes[] = { MENU_Y(224.0f), MENU_Y(500.0f), MENU_Y(775.0f) };
	for (float size : sizes) {
		for (int sx = -1; sx <= 1; sx += 2)
		for (int sy = -1; sy <= 1; sy += 2) {
			Map m = { size, SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2, 0, 0 };
			for (int i = 0; i < 2000; i++)
				pan(m, sx * 3.0f, sy * 3.0f);
			float ax, ay;
			atlas(m, ax, ay);
			if (!((sx < 0 ? ax <= 0.01f : ax >= 319.99f) && (sy < 0 ? ay <= 0.01f : ay >= 219.99f))) {
				fprintf(stderr, "corner (%d,%d) unreachable at size %.1f: atlas (%.2f,%.2f)\n", sx, sy, size, ax, ay);
				return 1;
			}
			assert(fabsf(m.ox) <= SCREEN_WIDTH / 2 && fabsf(m.oy) <= SCREEN_HEIGHT / 2);
		}
	}

	// Zoomed in: the map scrolls, the crosshair stays centred.
	Map m = { MENU_Y(775.0f), SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2, 0, 0 };
	pan(m, 10.0f, -10.0f);
	assert(m.ox == 0.0f && m.oy == 0.0f);
	assert(m.cx == SCREEN_WIDTH / 2 - 10.0f && m.cy == SCREEN_HEIGHT / 2 + 10.0f);

	// Push past the right edge, then come back: crosshair snaps to centre.
	for (int i = 0; i < 2000; i++)
		pan(m, 3.0f, 0.0f);
	assert(m.ox > 0.0f);
	const float edge = m.cx;
	pan(m, -(m.ox + 5.0f), 0.0f);
	assert(m.ox == 0.0f && m.cx == edge + 5.0f);

	// Min zoom fits the screen: the map never moves, only the crosshair.
	Map small = { MENU_Y(224.0f), SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2, 0, 0 };
	pan(small, 7.0f, -4.0f);
	assert(small.cx == SCREEN_WIDTH / 2 && small.cy == SCREEN_HEIGHT / 2);
	assert(small.ox == 7.0f && small.oy == -4.0f);

	// Screen <-> world round trip.
	CVector2D w = MapScreenToWorld3DS(CVector2D(123.0f, 77.0f), MENU_Y(500.0f), 150.0f, 130.0f);
	CVector2D s = MapWorldToScreen3DS(w, MENU_Y(500.0f), 150.0f, 130.0f);
	assert(fabsf(s.x - 123.0f) < 0.01f && fabsf(s.y - 77.0f) < 0.01f);

	printf("ok\n");
	return 0;
}
"""
        build_and_run(stub)


if __name__ == "__main__":
    unittest.main()
