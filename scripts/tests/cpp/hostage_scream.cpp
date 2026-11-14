// Harness for test_hostage_scream.py: the bHeldHostageInCar block of
// CPed::ProcessControl (stories/src/peds/Ped.cpp) is pasted in at BLOCK.
#include <cassert>
enum { MI_AMBULAN = 147, MI_TAXI = 151, MI_CABBIE = 166, MI_IDAHO = 132 };
enum { SOUND_PED_FLEE_SPRINT = 120 };

struct CPed;
struct CVehicle {
	int model;
	CPed *pDriver;
	int GetModelIndex() { return model; }
};

struct CPed {
	bool player;
	CVehicle *m_pMyVehicle;
	bool bHeldHostageInCar;
	bool bHostageScreamed;
	int says;
	bool IsPlayer() { return player; }
	void Say(int) { says++; }
	void Process() {
/*@BLOCK@*/
	}
};

static int framesOfScreaming(int model) {
	CPed player = { true };
	CVehicle car = { model, &player };
	CPed passenger = { false, &car, true, false, 0 };
	for (int i = 0; i < 30; i++)
		passenger.Process();
	return passenger.says;
}

int main() {
	// PS2 0x1d6f30: one scream per hostage, not one per frame.
	assert(framesOfScreaming(MI_IDAHO) == 1);
	// PS2 0x32a5e0: no scream in a taxi, cabbie or ambulance (taxi fares).
	assert(framesOfScreaming(MI_TAXI) == 0);
	assert(framesOfScreaming(MI_CABBIE) == 0);
	assert(framesOfScreaming(MI_AMBULAN) == 0);
	return 0;
}
