// Harness for test_3ds_ps2_follow_ped_cam.py: the PS2FollowPed* pure-math
// helpers from stories/src/core/Cam.cpp are pasted in at the marker below.
#include "stubs.h"
#include "scenarios.h"

/*@FUNCTIONS@*/

static void look_down_per_zoom() {
	float z1 = PS2FollowPedLookDown(0.06f);
	float z2 = PS2FollowPedLookDown(-0.1f);
	float z3 = PS2FollowPedLookDown(-0.07f);
	assert(Abs(z1 - 0.21f) < 0.001f);
	assert(Abs(z2 - 0.05f) < 0.001f);
	assert(Abs(z3 - 0.08f) < 0.001f);
}

static void string_dist_follows_zoom() {
	// Zoom growing (Select zoom-out) pushes out even with a short string.
	assert(Abs(PS2FollowPedStringDist(2.25f, 2.5f, 2.25f) - 4.5f) < 0.0001f);
	// Zoom shrinking pulls straight in.
	assert(Abs(PS2FollowPedStringDist(4.5f, 0.0f, 4.5f) - 2.0f) < 0.0001f);
	// Steady zoom: string length kept within [2, maxDist].
	assert(Abs(PS2FollowPedStringDist(3.0f, 2.5f, 4.5f) - 3.0f) < 0.0001f);
	assert(Abs(PS2FollowPedStringDist(1.0f, 2.5f, 4.5f) - 2.0f) < 0.0001f);
	assert(Abs(PS2FollowPedStringDist(9.0f, 2.5f, 4.5f) - 4.5f) < 0.0001f);
	// maxDist == 2: always 2.
	assert(Abs(PS2FollowPedStringDist(1.0f, 0.0f, 2.0f) - 2.0f) < 0.0001f);
}

static void pitch_step_converges_and_respects_cap() {
	// Far from target: step is capped at 0.1*dt.
	float a = PS2FollowPedPitchStep(1.0f, 0.0f, 1.0f);
	assert(Abs(a - 0.1f) < 0.0001f);
	// Already at target: no movement.
	float b = PS2FollowPedPitchStep(0.3f, 0.3f, 1.0f);
	assert(Abs(b - 0.3f) < 0.0001f);
	// dt = 0 is a no-op.
	float c = PS2FollowPedPitchStep(1.0f, 0.2f, 0.0f);
	assert(Abs(c - 0.2f) < 0.0001f);
}

static void stick_target_is_quadratic_and_signed() {
	float gain = 1.0f/1120.0f;
	float pos = PS2FollowPedStickTarget(64.0f, gain, 70.0f);
	float neg = PS2FollowPedStickTarget(-64.0f, gain, 70.0f);
	assert(Abs(pos - 0.007f*0.007f*64.0f*64.0f*gain*70.0f) < 0.00001f);
	assert(Abs(pos + neg) < 0.00001f);
	// Doubling the deflection quadruples the target.
	assert(Abs(PS2FollowPedStickTarget(128.0f, gain, 70.0f) - 4.0f*pos) < 0.00001f);
	assert(PS2FollowPedStickTarget(0.0f, gain, 70.0f) == 0.0f);
}

static void speed_step_smooths_clamps_and_snaps() {
	// Target clamped to 0.1, then blended at (1-0.8^dt).
	assert(Abs(PS2FollowPedSpeedStep(1.0f, 0.0f, 1.0f) - 0.02f) < 0.0001f);
	assert(Abs(PS2FollowPedSpeedStep(-1.0f, 0.0f, 1.0f) + 0.02f) < 0.0001f);
	// No target: previous speed decays by 0.8^dt instead of stopping dead.
	assert(Abs(PS2FollowPedSpeedStep(0.0f, 0.05f, 1.0f) - 0.04f) < 0.0001f);
	// Tiny speed snaps to zero.
	assert(PS2FollowPedSpeedStep(0.0f, 0.0001f, 1.0f) == 0.0f);
}

static void auto_rotate_step_caps_and_thresholds() {
	// Stopped ped: no auto-rotate.
	assert(Abs(PS2FollowPedAutoRotateStep(1.0f, 0.0f, 1.0f, false, false)) < 0.0001f);
	// Already behind: no auto-rotate.
	assert(Abs(PS2FollowPedAutoRotateStep(0.0f, 5.0f, 1.0f, false, false)) < 0.0001f);
	// Fast-moving ped, big delta: capped at 0.02*dt.
	float step = PS2FollowPedAutoRotateStep(1.0f, 10.0f, 1.0f, false, false);
	assert(Abs(step - 0.02f) < 0.0001f);
	// Sign follows betaDelta.
	float negStep = PS2FollowPedAutoRotateStep(-1.0f, 10.0f, 1.0f, false, false);
	assert(Abs(negStep + 0.02f) < 0.0001f);
	// Small delta: proportional, so it settles instead of overshooting.
	assert(Abs(PS2FollowPedAutoRotateStep(0.01f, 10.0f, 1.0f, false, false) - 0.01f) < 0.0001f);
	assert(Abs(PS2FollowPedAutoRotateStep(0.01f, 2.0f, 1.0f, false, false) - 0.002f) < 0.0001f);
	// Ped walking at the camera (>=170deg): no auto-rotate.
	assert(PS2FollowPedAutoRotateStep(DEGTORAD(171.0f), 10.0f, 1.0f, false, false) == 0.0f);
	// Force-behind latch: ignores ped speed, doubles the cap, no 170deg cutoff.
	assert(Abs(PS2FollowPedAutoRotateStep(1.0f, 0.0f, 1.0f, true, false) - 0.04f) < 0.0001f);
	assert(Abs(PS2FollowPedAutoRotateStep(0.2f, 0.0f, 1.0f, true, false) - 0.02f) < 0.0001f);
	assert(Abs(PS2FollowPedAutoRotateStep(DEGTORAD(171.0f), 0.0f, 1.0f, true, false) - 0.04f) < 0.0001f);
	// Firing a two-handed gun: latched rates x2.5, no 170deg cutoff, even unlatched.
	assert(Abs(PS2FollowPedAutoRotateStep(1.0f, 0.0f, 1.0f, false, true) - 0.1f) < 0.0001f);
	assert(Abs(PS2FollowPedAutoRotateStep(0.2f, 0.0f, 1.0f, true, true) - 0.05f) < 0.0001f);
	assert(Abs(PS2FollowPedAutoRotateStep(-DEGTORAD(171.0f), 0.0f, 1.0f, false, true) + 0.1f) < 0.0001f);
}

static void level_pitch_eases_toward_level() {
	assert(Abs(PS2FollowPedLevelPitch(0.5f, 1.0f) - 0.45f) < 0.0001f);
	assert(Abs(PS2FollowPedLevelPitch(-1.0f, 1.0f) + 0.9f) < 0.0001f);
	// Capped at 0.16*dt.
	assert(Abs(PS2FollowPedLevelPitch(10.0f, 1.0f) - 9.84f) < 0.0001f);
	assert(PS2FollowPedLevelPitch(0.0f, 1.0f) == 0.0f);
}

int main(int argc, char **argv) {
	SCENARIOS_BEGIN
	SCENARIO(look_down_per_zoom)
	SCENARIO(string_dist_follows_zoom)
	SCENARIO(pitch_step_converges_and_respects_cap)
	SCENARIO(stick_target_is_quadratic_and_signed)
	SCENARIO(speed_step_smooths_clamps_and_snaps)
	SCENARIO(auto_rotate_step_caps_and_thresholds)
	SCENARIO(level_pitch_eases_toward_level)
	SCENARIOS_END
}
