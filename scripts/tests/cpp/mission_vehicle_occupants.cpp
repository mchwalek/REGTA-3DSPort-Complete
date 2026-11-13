// Evaluates RenderOneNonRoad's 3DS occupant gate extracted from Renderer.cpp.
#include <cassert>

typedef int RpClump;
enum { RANDOM_VEHICLE = 1, MISSION_VEHICLE = 2 };
struct CVehicle { int VehicleCreatedBy; };
static bool highDetail;
struct CVisibilityPlugins {
	static bool IsVehicleHighDetail(RpClump *, bool) { return highDetail; }
};

static bool Gate(CVehicle *veh, RpClump *vehicleClump, bool bigVehicle, bool lod0)
{
	highDetail = lod0;
	bool renderOccupants;
	/*@GATE@*/
	return renderOccupants;
}

int main()
{
	RpClump clump = 0;
	CVehicle mission = { MISSION_VEHICLE }, random = { RANDOM_VEHICLE };
	// Massimo in the JDT7 maverick: mission heli beyond lod0 keeps its passengers
	assert(Gate(&mission, &clump, true, false));
	assert(Gate(&mission, &clump, true, true));
	// traffic still drops occupants past lod0
	assert(!Gate(&random, &clump, false, false));
	assert(Gate(&random, &clump, false, true));
	assert(!Gate(&mission, nullptr, true, true));
	return 0;
}
