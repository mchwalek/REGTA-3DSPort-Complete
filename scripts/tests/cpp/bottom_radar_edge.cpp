// Harness for test_3ds_bottom_radar_edge.py: LimitBottomRadarPoint3DS from
// stories/src/core/Radar.cpp is pasted in at the marker below.
#include "stubs.h"
#include "scenarios.h"

/*@FUNCTION@*/

static const float kLeft = -11.0f / 12.0f;
static const float kRight = 19.0f / 12.0f;
static const float kVertical = 11.0f / 12.0f;
static const float kEps = 1e-5f;

static bool Near(float a, float b) { return fabsf(a - b) < kEps; }

static bool OnEdge(const CVector2D &p)
{
	return Near(p.x, kLeft) || Near(p.x, kRight) || Near(p.y, kVertical) || Near(p.y, -kVertical);
}

static void corner_inside()
{
	CVector2D p(0.85f, 0.85f);
	float edge = LimitBottomRadarPoint3DS(p);
	assert(p.x == 0.85f && p.y == 0.85f);
	assert(edge <= 1.0f);
	CVector2D q(-0.9f, -0.9f);
	assert(LimitBottomRadarPoint3DS(q) <= 1.0f && q.x == -0.9f && q.y == -0.9f);
}

static void under_rail()
{
	CVector2D p(1.5f, 0.0f);
	float edge = LimitBottomRadarPoint3DS(p);
	assert(p.x == 1.5f && p.y == 0.0f);
	assert(edge <= 1.0f);
}

static void far_points()
{
	const CVector2D in[] = { CVector2D(5.0f, 0.0f), CVector2D(-5.0f, 0.0f), CVector2D(0.0f, 5.0f), CVector2D(0.0f, -5.0f),
	                         CVector2D(5.0f, 5.0f), CVector2D(-5.0f, -3.0f), CVector2D(-2.0f, 0.0f) };
	for (const CVector2D &src : in) {
		CVector2D p = src;
		float edge = LimitBottomRadarPoint3DS(p);
		assert(edge > 1.0f);
		assert(OnEdge(p));
		assert(p.x >= kLeft - kEps && p.x <= kRight + kEps && fabsf(p.y) <= kVertical + kEps);
		// same direction: p == src / edge
		assert(Near(p.x * edge, src.x) && Near(p.y * edge, src.y));
	}
	CVector2D left(-2.0f, 0.0f);
	LimitBottomRadarPoint3DS(left);
	assert(Near(left.x, kLeft));
}

static void on_edge()
{
	CVector2D p(kRight, 0.0f);
	float edge = LimitBottomRadarPoint3DS(p);
	assert(Near(edge, 1.0f));
	assert(Near(p.x, kRight) && p.y == 0.0f);
	CVector2D q(0.0f, -kVertical);
	assert(Near(LimitBottomRadarPoint3DS(q), 1.0f));
}

static void linear()
{
	const CVector2D in[] = { CVector2D(0.3f, 0.2f), CVector2D(-0.4f, 0.1f), CVector2D(1.0f, -0.6f) };
	for (const CVector2D &src : in) {
		CVector2D a = src, b(src.x * 2.0f, src.y * 2.0f);
		float ea = LimitBottomRadarPoint3DS(a);
		float eb = LimitBottomRadarPoint3DS(b);
		assert(Near(eb, 2.0f * ea));
	}
}

static void origin()
{
	CVector2D p(0.0f, 0.0f);
	assert(LimitBottomRadarPoint3DS(p) == 0.0f);
	assert(p.x == 0.0f && p.y == 0.0f);
}

static void north_distance()
{
	for (int i = 0; i < 360; i++) {
		float a = i * 3.14159265f / 180.0f;
		CVector2D p(2.0f * cosf(a), 2.0f * sinf(a));
		assert(LimitBottomRadarPoint3DS(p) > 1.0f);
		assert(OnEdge(p));
	}
}

int main(int argc, char **argv)
{
	SCENARIOS_BEGIN
	SCENARIO(corner_inside)
	SCENARIO(under_rail)
	SCENARIO(far_points)
	SCENARIO(on_edge)
	SCENARIO(linear)
	SCENARIO(origin)
	SCENARIO(north_distance)
	SCENARIOS_END
}
