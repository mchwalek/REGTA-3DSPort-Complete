#!/usr/bin/env python3
"""Regression test for the 3DS map pan-limit macros (MAP_PAN_LIMIT_X/_Y)
and the always-true-on-3DS horizontal-pan gate (CAN_PAN_X_AT_CURRENT_ZOOM).

On 3DS the map crosshair is pinned to screen centre (there is no mouse), so
reaching a given map point means panning that point to screen centre. The
pan clamp must therefore allow m_fMapCenterX/Y to range across the map's
own true half-extent (the 320x220 atlas -- see
CRadar::TransformRadarPointToScreenSpace and CMenuManager::PrintMap), not
the PC-only `m_fMapSize - MAP_MIN_SIZE` formula, which falls short of the
map edges (that's the bug this macro fixes).

Extracts the real MAP_PAN_LIMIT_X/_Y/CAN_PAN_X_AT_CURRENT_ZOOM macros and
the real screen->atlas conversion snippet from the waypoint hit-test (both
in Frontend.cpp), compiles them against a minimal stub, and asserts the
screen-centre crosshair can reach all four atlas corners (0,0) and
(320,220) at both minimum and maximum zoom.
"""
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FRONTEND_CPP = ROOT / "stories" / "src" / "core" / "Frontend.cpp"


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
    def test_pan_limit_reaches_all_atlas_corners(self):
        source = FRONTEND_CPP.read_text()

        pan_limit_macros = extract(
            source,
            "#ifdef _3DS\n// Fixed centre crosshair",
            "#define MAX_VISIBLE_LIST_ROW",
        )

        # Extracted in two pieces to skip the screen-rect containment guard
        # (`if (mapCrosshair.y > ... ) {`) sitting between them -- that
        # guard is about whether a click lands inside the rendered map
        # widget at all, not about the pan-limit math under test here, and
        # pulling it in verbatim would leave an unmatched brace.
        map_half_width = extract(
            source,
            "const float mapHalfWidth = m_fMapSize * (320.0f / 220.0f);",
            "if (mapCrosshair.y",
        )
        conversion_body = extract(
            source,
            "const float sourceScale = m_fMapSize * 2.0f / 220.0f;",
            "(m_fMapCenterY - m_fMapSize)) / sourceScale;",
        ) + "(m_fMapCenterY - m_fMapSize)) / sourceScale;"
        screen_to_atlas = map_half_width + conversion_body

        stub = r"""
#include <cassert>
#include <cmath>
#include <cstdio>

#define _3DS
#define Clamp(v, low, high) ((v)<(low) ? (low) : (v)>(high) ? (high) : (v))
#define MENU_X(x) (x)
#define MENU_Y(y) (y)
#define SCREEN_WIDTH 400.0f
#define SCREEN_HEIGHT 240.0f
#define MAP_MIN_SIZE 224.f

""" + pan_limit_macros + r"""

struct V2 { float x, y; };

/* Mirrors the real reachability check: clamp m_fMapCenterX/Y to the new
 * limit, with the crosshair fixed at screen centre (as it always is on
 * 3DS), then run the real screen->atlas conversion and check the result
 * reaches the expected atlas corner. */
static void check_reachable(float mapSize, float cx, float cy,
                             float expectedAtlasX, float expectedAtlasY) {
	V2 mapCrosshair = { SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2 };
	float m_fMapSize = mapSize;
	float m_fMapCenterX = cx;
	float m_fMapCenterY = cy;

	""" + screen_to_atlas + r"""

	if (fabsf(sourceX - expectedAtlasX) > 0.01f || fabsf(sourceY - expectedAtlasY) > 0.01f) {
		fprintf(stderr, "unreachable at mapSize=%.1f center=(%.2f,%.2f): got atlas (%.3f,%.3f), want (%.3f,%.3f)\n",
			mapSize, cx, cy, sourceX, sourceY, expectedAtlasX, expectedAtlasY);
		assert(false);
	}
}

int main() {
	assert(CAN_PAN_X_AT_CURRENT_ZOOM);

	float zoomLevels[] = { MENU_Y(MAP_MIN_SIZE), MENU_Y(1000.0f) };
	for (float mapSize : zoomLevels) {
		float limitX = MAP_PAN_LIMIT_X(mapSize);
		float limitY = MAP_PAN_LIMIT_Y(mapSize);

		float lowX = SCREEN_WIDTH/2 - limitX, highX = limitX + SCREEN_WIDTH/2;
		float lowY = SCREEN_HEIGHT/2 - limitY, highY = limitY + SCREEN_HEIGHT/2;

		/* Top-left atlas corner (0,0) requires panning the map's own
		 * top-left to screen centre, i.e. m_fMapCenterX/Y at their
		 * highest clamp value. */
		check_reachable(mapSize, highX, highY, 0.0f, 0.0f);
		/* Bottom-right atlas corner (320,220) requires the opposite
		 * extreme. */
		check_reachable(mapSize, lowX, lowY, 320.0f, 220.0f);
	}
	printf("ok\n");
	return 0;
}
"""
        build_and_run(stub)


if __name__ == "__main__":
    unittest.main()
