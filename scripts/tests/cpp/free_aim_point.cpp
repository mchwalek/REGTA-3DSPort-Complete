// Harness for test_3ds_free_aim_point.py: Update3DSFreeAimPointAngles from
// stories/src/core/Cam.cpp is pasted in at the marker below.
#include "stubs.h"
#include "scenarios.h"

struct CGeneral {
	static float GetATanOfXY(float x, float y) {
		float arc = atan2f(y, x);
		if (arc < 0.0f) arc += 2.0f * PI;
		return arc;
	}
	static float LimitRadianAngle(float angle) {
		float result = angle;
		if (result < -25.0f) result = -25.0f;
		if (result > 25.0f) result = 25.0f;
		while (result >= PI) result -= 2.0f * PI;
		while (result < -PI) result += 2.0f * PI;
		return result;
	}
};

/*@FUNCTION@*/

static float PitchFromPed(const CVector &point, const CVector &pedPos) {
	CVector fromPed = point - pedPos;
	return RADTODEG(Acos(Clamp(fromPed.z / fromPed.Magnitude(), -1.0f, 1.0f)));
}

static void full_down_stick_converges_and_stops_at_110() {
	CVector pedPos(0.0f, 0.0f, 0.0f);
	CVector pedForward(0.0f, 1.0f, 0.0f);
	CVector pivot(0.0f, 0.0f, 0.6f);
	float range = 30.0f;
	CVector point = pedPos + pedForward * range;
	float prevYawRel = 0.0f;

	for (int i = 0; i < 400; i++)
		Update3DSFreeAimPointAngles(point, prevYawRel, pedPos, pedForward, pivot, range, 0.0f, -128.0f, 1.0f);

	float pitch = PitchFromPed(point, pedPos);
	assert(pitch > 108.0f && pitch < 112.0f);

	// Further downward input must not push past the envelope.
	Update3DSFreeAimPointAngles(point, prevYawRel, pedPos, pedForward, pivot, range, 0.0f, -128.0f, 1.0f);
	assert(PitchFromPed(point, pedPos) <= 110.5f);
}

static void recovers_from_below_floor_with_hysteresis() {
	CVector pedPos(0.0f, 0.0f, 0.0f);
	CVector pedForward(0.0f, 1.0f, 0.0f);
	CVector pivot(0.0f, 0.0f, 0.6f);
	float range = 30.0f;
	// Start the point well past the 110-degree floor -- simulates a state
	// outside the envelope. Use a properly-conditioned 150-degree-from-
	// vertical direction (real horizontal component) rather than a near-
	// polar-singular one, so pitch isn't pinned across iterations.
	float theta = DEGTORAD(150.0f);
	CVector point = pedPos + CVector(sinf(theta), 0.0f, cosf(theta)) * range;
	float prevYawRel = 0.0f;

	float startPitch = PitchFromPed(point, pedPos);
	assert(startPitch > 110.0f);

	// Stick up (positive stickY) must move the point back toward the band.
	for (int i = 0; i < 2000; i++)
		Update3DSFreeAimPointAngles(point, prevYawRel, pedPos, pedForward, pivot, range, 0.0f, 128.0f, 1.0f);

	float pitch = PitchFromPed(point, pedPos);
	assert(pitch < startPitch);
	assert(pitch <= 110.5f);
}

static void yaw_cone_stops_at_110_and_reenters_on_reverse() {
	CVector pedPos(0.0f, 0.0f, 0.0f);
	CVector pedForward(0.0f, 1.0f, 0.0f);
	CVector pivot(0.0f, 0.0f, 0.6f);
	float range = 30.0f;
	CVector point = pedPos + pedForward * range;
	float prevYawRel = 0.0f;

	for (int i = 0; i < 400; i++)
		Update3DSFreeAimPointAngles(point, prevYawRel, pedPos, pedForward, pivot, range, 128.0f, 0.0f, 1.0f);

	assert(Abs(RADTODEG(prevYawRel)) > 108.0f && Abs(RADTODEG(prevYawRel)) < 112.0f);
	float relBefore = prevYawRel;

	// Further same-direction input must not push past the cone.
	Update3DSFreeAimPointAngles(point, prevYawRel, pedPos, pedForward, pivot, range, 128.0f, 0.0f, 1.0f);
	assert(Abs(RADTODEG(prevYawRel)) <= 110.5f);

	// Reverse input re-enters the cone (moves relative angle back down).
	Update3DSFreeAimPointAngles(point, prevYawRel, pedPos, pedForward, pivot, range, -128.0f, 0.0f, 1.0f);
	assert(Abs(prevYawRel) < Abs(relBefore) + 1e-4f);
}

static void point_stays_at_range_from_pivot_after_accepted_yaw() {
	CVector pedPos(0.0f, 0.0f, 0.0f);
	CVector pedForward(0.0f, 1.0f, 0.0f);
	CVector pivot(0.0f, 0.0f, 0.6f);
	float range = 30.0f;
	CVector point = pedPos + pedForward * range;
	float prevYawRel = 0.0f;

	for (int i = 0; i < 50; i++) {
		Update3DSFreeAimPointAngles(point, prevYawRel, pedPos, pedForward, pivot, range, 40.0f, 0.0f, 1.0f);
		float dist = (point - pivot).Magnitude();
		assert(dist > range - 0.01f && dist < range + 0.01f);
	}
}

static void zero_dt_is_a_noop() {
	CVector pedPos(0.0f, 0.0f, 0.0f);
	CVector pedForward(0.0f, 1.0f, 0.0f);
	CVector pivot(0.0f, 0.0f, 0.6f);
	float range = 30.0f;
	CVector point = pivot + pedForward * range;
	float prevYawRel = 0.0f;
	CVector before = point;
	float prevBefore = prevYawRel;

	Update3DSFreeAimPointAngles(point, prevYawRel, pedPos, pedForward, pivot, range, 100.0f, -100.0f, 0.0f);

	assert(point.x == before.x && point.y == before.y && point.z == before.z);
	assert(prevYawRel == prevBefore);
}

int main(int argc, char **argv) {
	SCENARIOS_BEGIN
	SCENARIO(full_down_stick_converges_and_stops_at_110)
	SCENARIO(recovers_from_below_floor_with_hysteresis)
	SCENARIO(yaw_cone_stops_at_110_and_reenters_on_reverse)
	SCENARIO(point_stays_at_range_from_pivot_after_accepted_yaw)
	SCENARIO(zero_dt_is_a_noop)
	SCENARIOS_END
}
