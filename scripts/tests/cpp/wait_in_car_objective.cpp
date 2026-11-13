// Harness for test_wait_in_car_objective.py: the OBJECTIVE_WAIT_IN_CAR case of
// CPed::ProcessObjective (stories/src/peds/PedAI.cpp) is pasted in at CASE.
#include <cassert>
enum { OBJECTIVE_NONE, OBJECTIVE_WAIT_IN_CAR, OBJECTIVE_WAIT_IN_CAR_THEN_GET_OUT };
enum { PED_IDLE, PED_DRIVING };

struct CPed {
	bool bInVehicle;
	int m_objective;
	int m_nPedState;
	void SetPedState(int s) { m_nPedState = s; }
	void ProcessObjective() {
		switch (m_objective) {
/*@CASE@*/
		default: break;
		}
	}
};

int main() {
	// Ped seated in a vehicle keeps waiting in it.
	CPed seated = { true, OBJECTIVE_WAIT_IN_CAR, PED_IDLE };
	seated.ProcessObjective();
	assert(seated.m_nPedState == PED_DRIVING);
	assert(seated.m_objective == OBJECTIVE_WAIT_IN_CAR);

	// WAIT_IN_CAR restored after LEAVE_CAR on a ped now on foot (JDT7 Massimo):
	// must not become PED_DRIVING, or nothing renders him.
	CPed onFoot = { false, OBJECTIVE_WAIT_IN_CAR, PED_IDLE };
	onFoot.ProcessObjective();
	assert(onFoot.m_nPedState == PED_IDLE);
	assert(onFoot.m_objective == OBJECTIVE_NONE);
	return 0;
}
