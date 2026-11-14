// Harness for test_3ds_look_behind_cam_in_front.py: LookBehindCamIsInFront3DS
// from stories/src/core/Cam.cpp is pasted in at the marker below.
#include "stubs.h"
#include "scenarios.h"

static float DotProduct2D(const CVector &a, const CVector &b) { return a.x * b.x + a.y * b.y; }

/*@FUNCTION@*/

static const CVector car(100.0f, 50.0f, 10.0f);
static const CVector carFwd(0.6f, 0.8f, 0.0f);

static void chase_cam_behind_car_is_not_in_front() {
	// Process_Cam_On_A_String and Process_FollowCar_SA both trail the car; only their Beta convention differs.
	assert(!LookBehindCamIsInFront3DS(car - carFwd * 8.0f + CVector(0.0f, 0.0f, 2.0f), car, carFwd));
	assert(!LookBehindCamIsInFront3DS(car - carFwd * 8.0f + CVector(-carFwd.y, carFwd.x, 0.0f) * 5.0f, car, carFwd));
}

static void cam_ahead_of_car_is_in_front() {
	assert(LookBehindCamIsInFront3DS(car + carFwd * 8.0f, car, carFwd));
	assert(LookBehindCamIsInFront3DS(car + carFwd * 2.0f + CVector(carFwd.y, -carFwd.x, 0.0f) * 5.0f, car, carFwd));
}

int main(int argc, char **argv) {
	SCENARIOS_BEGIN
	SCENARIO(chase_cam_behind_car_is_not_in_front)
	SCENARIO(cam_ahead_of_car_is_in_front)
	SCENARIOS_END
}
