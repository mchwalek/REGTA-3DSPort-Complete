// Harness for test_3ds_scope_size.py: GetPS2ScopeRect3DS from
// stories/src/renderer/Hud.cpp is pasted in at the marker below.
#include "stubs.h"

#define SCREEN_WIDTH 400.0f
#define SCREEN_HEIGHT 240.0f
#define PSP_DEFAULT_SCREEN_HEIGHT (272)

// Same field order and constructor as stories/src/math/Rect.h.
struct CRect {
	float left, bottom, right, top;
	CRect(float l, float t, float r, float b) : left(l), bottom(b), right(r), top(t) {}
};

/*@HELPER@*/

static bool near(float a, float b) { return fabsf(a - b) < 0.01f; }

int main() {
	// PS2 widescreen sniper/laser quadrants: 210 x 210 PSP units (SLES_541.35 0x23f540).
	const float half = 210.0f * 240.0f / 272.0f;
	CRect r = GetPS2ScopeRect3DS(210.0f, 210.0f);
	if (!(near(r.left, 200.0f - half) && near(r.right, 200.0f + half) &&
	      near(r.top, 120.0f - half) && near(r.bottom, 120.0f + half))) {
		fprintf(stderr, "rect (%.2f,%.2f)-(%.2f,%.2f), want half-extent %.2f\n",
			r.left, r.top, r.right, r.bottom, half);
		return 1;
	}
	// The circle fills the screen height and stays inside the screen width.
	assert(r.top < 0.0f && r.bottom > SCREEN_HEIGHT);
	assert(r.left >= 0.0f && r.right <= SCREEN_WIDTH);
	// One scale on both axes: the scope is round, not an ellipse.
	assert(near(r.right - r.left, r.bottom - r.top));

	printf("ok\n");
	return 0;
}
