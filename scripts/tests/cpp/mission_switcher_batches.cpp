// Harness for test_mission_switcher_batches.py: SameMissionBatch,
// MissionBatchStart, StepMissionBatch and the missions[] table from
// stories/src/core/re3.cpp are pasted in at the markers below.
#include <cassert>
#include <cstring>
typedef int int32;
#define nil nullptr

/*@FUNCTIONS@*/

/*@MISSIONS@*/

static int32 find(const char *name) {
	for (int32 i = 0; i < (int32)(sizeof(missions) / sizeof(missions[0])); i++)
		if (strcmp(missions[i], name) == 0) return i;
	assert(!"missing");
	return -1;
}

int main() {
	const int32 n = sizeof(missions) / sizeof(missions[0]);
	const int32 side = find("Home Sweet Home"), vin = find("Slacker (Vincenzo)"),
		sal = find("The Offer (Salvatore)"), tosh = find("More Deadly than the Male (Toshiko Kasen)");
	assert(StepMissionBatch(missions, n, 0, 1) == side);          // initial -> side missions
	assert(StepMissionBatch(missions, n, find("Karmageddon"), 1) == vin);
	assert(StepMissionBatch(missions, n, vin, 1) == sal);
	assert(StepMissionBatch(missions, n, find("Snuff (Vincenzo)"), -1) == vin); // mid-batch: own start
	assert(StepMissionBatch(missions, n, vin, -1) == side);       // at start: previous batch
	assert(StepMissionBatch(missions, n, n - 1, 1) == 0);         // wraps forward
	assert(StepMissionBatch(missions, n, 0, -1) == tosh);         // wraps backward
	assert(StepMissionBatch(missions, n, find("Making Toni (Salvatore)"), -1) == find("Shop 'til you Strop (Maria)"));
	assert(StepMissionBatch(missions, n, find("L.C. Confidential (Church Confessional)"), 1) == find("Rough Justice (Salvatore)"));
	return 0;
}
