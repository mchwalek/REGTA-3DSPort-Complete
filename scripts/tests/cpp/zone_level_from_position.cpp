// Harness for test_zone_level_from_position.py: CTheZones::GetLevelFromPosition
// from stories/src/core/Zones.cpp is pasted in at the marker below.
#include "stubs.h"
#include "scenarios.h"

enum eLevelName { LEVEL_GENERIC, LEVEL_INDUSTRIAL, LEVEL_COMMERCIAL, LEVEL_SUBURBAN, LEVEL_UNDERGROUND };
struct CZone { float minx, miny, minz, maxx, maxy, maxz; eLevelName level; };
struct CGame { static eLevelName currLevel; };
eLevelName CGame::currLevel;
struct CTheZones {
	static CZone MapZoneArray[8];
	static int TotalNumberOfMapZones;
	static bool PointLiesWithinZone(const CVector *v, CZone *zone) {
		return zone->minx <= v->x && v->x <= zone->maxx && zone->miny <= v->y && v->y <= zone->maxy &&
		       zone->minz <= v->z && v->z <= zone->maxz;
	}
	static eLevelName GetLevelFromPosition(CVector const *v);
};
CZone CTheZones::MapZoneArray[8];
int CTheZones::TotalNumberOfMapZones;

/*@FUNCTION@*/

static void zone(eLevelName l, float minx, float maxx) {
	CZone z = { minx, -10.0f, -10.0f, maxx, 10.0f, 10.0f, l };
	CTheZones::MapZoneArray[CTheZones::TotalNumberOfMapZones++] = z;
}

static eLevelName at(float x, eLevelName cur) {
	CVector v(x, 0.0f, 0.0f);
	CGame::currLevel = cur;
	return CTheZones::GetLevelFromPosition(&v);
}

static void setup() {
	zone(LEVEL_GENERIC, -1000.0f, 1000.0f); // whole map
	zone(LEVEL_COMMERCIAL, 0.0f, 10.0f);
	zone(LEVEL_INDUSTRIAL, 5.0f, 20.0f);
	zone(LEVEL_UNDERGROUND, 15.0f, 30.0f);
	zone(LEVEL_UNDERGROUND, 40.0f, 50.0f);
	zone(LEVEL_SUBURBAN, 45.0f, 60.0f);
}

// x=7 is in both Staunton and Portland: no swap from either side.
static void overlap_keeps_current_level() {
	setup();
	assert(at(7.0f, LEVEL_COMMERCIAL) == LEVEL_COMMERCIAL);
	assert(at(7.0f, LEVEL_INDUSTRIAL) == LEVEL_INDUSTRIAL);
}

static void overlap_from_elsewhere_takes_last_match() {
	setup();
	assert(at(7.0f, LEVEL_SUBURBAN) == LEVEL_INDUSTRIAL);
	assert(at(7.0f, LEVEL_GENERIC) == LEVEL_INDUSTRIAL);
}

static void underground_only_counts_if_first_or_current() {
	setup();
	assert(at(17.0f, LEVEL_COMMERCIAL) == LEVEL_INDUSTRIAL);   // level 4 after a match is ignored
	assert(at(17.0f, LEVEL_UNDERGROUND) == LEVEL_UNDERGROUND); // ... unless already underground
	assert(at(25.0f, LEVEL_INDUSTRIAL) == LEVEL_UNDERGROUND);  // only a level-4 zone
	assert(at(47.0f, LEVEL_INDUSTRIAL) == LEVEL_SUBURBAN);     // level 4 first, then a real level
}

static void no_zone_is_generic() {
	setup();
	assert(at(35.0f, LEVEL_INDUSTRIAL) == LEVEL_GENERIC);
}

int main(int argc, char **argv) {
	SCENARIOS_BEGIN
	SCENARIO(overlap_keeps_current_level)
	SCENARIO(overlap_from_elsewhere_takes_last_match)
	SCENARIO(underground_only_counts_if_first_or_current)
	SCENARIO(no_zone_is_generic)
	SCENARIOS_END
}
