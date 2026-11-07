// Harness for test_3ds_map_pan_limit.py: the LCS_MENU_MAP_* registration
// from Radar.h and the MAP_PAN_LIMIT_X/_Y macros and screen<->world helpers
// from stories/src/core/Frontend.cpp are pasted in at the markers below.
#include "stubs.h"

#define _3DS
#include "../../../common/3ds/MapPan3DS.h"
#define SCREEN_WIDTH 400.0f
#define SCREEN_HEIGHT 240.0f
#define MENU_Y(y) ((y) * SCREEN_HEIGHT / 448.0f)

/*@REGISTRATION@*/
/*@MACROS@*/
/*@HELPERS@*/

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
