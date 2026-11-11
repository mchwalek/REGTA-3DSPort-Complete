// Harness for test_lock_on_closeness.py: LockOnCloseness from
// stories/src/peds/PlayerPed.cpp is pasted in at the marker below.
#include "stubs.h"

/*@FUNCTION@*/

int main() {
	/* Base formula: 10 m at 0 rad, no bonuses. */
	assert(LockOnCloseness(10.0f, 0.0f, false, false, false) == -10.0f);

	/* Angle term: 10 m at 0.2 rad -> -10 - 5*0.2 = -11. */
	assert(std::fabs(LockOnCloseness(10.0f, 0.2f, false, false, false) - -11.0f) < 1e-5f);
	/* Angle sign doesn't matter (Abs). */
	assert(std::fabs(LockOnCloseness(10.0f, -0.2f, false, false, false) - -11.0f) < 1e-5f);

	/* Each bonus applied alone. */
	assert(std::fabs(LockOnCloseness(10.0f, 0.0f, true, false, false) - 20.0f) < 1e-5f);   // -10 + 30
	assert(std::fabs(LockOnCloseness(10.0f, 0.0f, false, true, false) - 5.0f) < 1e-5f);    // -10 + 15
	assert(std::fabs(LockOnCloseness(10.0f, 0.0f, false, false, true) - 30.0f) < 1e-5f);   // -10 + 40

	/* All bonuses together. */
	assert(std::fabs(LockOnCloseness(10.0f, 0.0f, true, true, true) - 75.0f) < 1e-5f);     // -10 + 30 + 15 + 40

	/* Symptom case: a 12 m on-screen ped outscores a 25 m off-screen ped
	 * (neither priority nor mission-char, both at 0 rad). */
	float nearOnScreen = LockOnCloseness(12.0f, 0.0f, false, true, false);
	float farOffScreen = LockOnCloseness(25.0f, 0.0f, false, false, false);
	assert(nearOnScreen > farOffScreen);

	/* Mission-char bonus can flip a ranking a closer ordinary ped would
	 * otherwise win: 20 m mission-char ped vs 10 m ordinary ped. */
	float missionCharFar = LockOnCloseness(20.0f, 0.0f, false, false, true);
	float ordinaryCloser = LockOnCloseness(10.0f, 0.0f, false, false, false);
	assert(missionCharFar > ordinaryCloser);

	printf("ok\n");
	return 0;
}
