// Harness for test_lcs_stats_save.py: CStats::SaveStats, LoadStats,
// InitLcsStats and the LCS stat setters (stories/src/core/Stats.cpp) are
// pasted in at FUNCTIONS, the CStats class from Stats.h at CLASS and its
// static member definitions at STATICS. OLD_FIELDS lists the stats block of
// saves written before the LCS-only stats, in save order. LCS_FIELDS lists
// the LCS-only stats in Stats.h order.
#include "stubs.h"
#include "scenarios.h"
#include <climits>
#include <vector>

#define Const const

/*@ENUMS@*/

/*@CLASS@*/

/*@STATICS@*/

/*@OLD_FIELDS@*/

/*@LCS_FIELDS@*/

struct CTimer {
	static uint32 ms;
	static uint32 GetTimeInMilliseconds() { return ms; }
};
uint32 CTimer::ms = 1000;

void CStats::PopulateFavoriteRadioStationList() {}

/*@FUNCTIONS@*/

static uint8 gBlock[8192];

#define SIZE_OF(f) + sizeof(CStats::f)
static const uint32 kOldSize = 0 OLD_FIELDS(SIZE_OF);
static const uint32 kLcsSize = 0 LCS_FIELDS(SIZE_OF);

static uint8 gSeed;
#define FILL(f) for (uint32 i = 0; i < sizeof(CStats::f); i++) ((uint8 *)&CStats::f)[i] = ++gSeed;
#define CLEAR(f) memset(&CStats::f, 0, sizeof(CStats::f));
#define SNAPSHOT(f) snap.insert(snap.end(), (uint8 *)&CStats::f, (uint8 *)&CStats::f + sizeof(CStats::f));
#define WRITE_OLD(f) memcpy(p, &CStats::f, sizeof(CStats::f)); p += sizeof(CStats::f);

static std::vector<uint8> Snapshot(bool old, bool lcs) {
	std::vector<uint8> snap;
	if (old) { OLD_FIELDS(SNAPSHOT) }
	if (lcs) { LCS_FIELDS(SNAPSHOT) }
	return snap;
}

// A save round-trips every field, and the old fields keep the old layout.
static void roundtrip() {
	OLD_FIELDS(FILL)
	LCS_FIELDS(FILL)
	uint32 size = 0;
	CStats::SaveStats(gBlock, &size);
	assert(size == kOldSize + kLcsSize);
	std::vector<uint8> saved = Snapshot(true, true);

	uint8 old[8192];
	uint8 *p = old;
	OLD_FIELDS(WRITE_OLD)
	assert(memcmp(old, gBlock, kOldSize) == 0);

	OLD_FIELDS(CLEAR)
	LCS_FIELDS(CLEAR)
	CTimer::ms = 4242;
	CStats::LoadStats(gBlock, size);
	assert(Snapshot(true, true) == saved);
	assert(CStats::SessionStartTime == 4242);
}

// A block from an older save has no LCS fields. They get the start values.
static void old_save() {
	CStats::InitLcsStats();
	std::vector<uint8> defaults = Snapshot(false, true);

	OLD_FIELDS(FILL)
	uint8 *p = gBlock;
	OLD_FIELDS(WRITE_OLD)
	std::vector<uint8> saved = Snapshot(true, false);

	OLD_FIELDS(CLEAR)
	LCS_FIELDS(FILL)
	CTimer::ms = 777;
	CStats::LoadStats(gBlock, kOldSize);
	assert(Snapshot(true, false) == saved);
	assert(Snapshot(false, true) == defaults);
	assert(CStats::SessionStartTime == 777);
}

// Prints every LCS field that InitLcsStats leaves non-zero.
#define PRINT_NONZERO(f) \
	for (uint32 i = 0; i < sizeof(CStats::f) / 4; i++) \
		if (((int32 *)&CStats::f)[i] != 0) printf(#f "[%u]=%d\n", i, ((int32 *)&CStats::f)[i]);
static void defaults() {
	LCS_FIELDS(FILL)
	CStats::InitLcsStats();
	LCS_FIELDS(PRINT_NONZERO)
	printf("UnlockedCostumes=%d\n", CStats::UnlockedCostumes);
}

static void setters() {
	CStats::InitLcsStats();
	// Smallest time wins, 0 means no time yet.
	CStats::RegisterFastestSmugglingTime(50);
	CStats::RegisterFastestSmugglingTime(70);
	CStats::RegisterFastestSmugglingTime(40);
	printf("smuggling=%d\n", CStats::FastestSmugglingTime);
	CStats::RegisterMostTimeLeftTrainRace(30);
	CStats::RegisterMostTimeLeftTrainRace(20);
	CStats::RegisterMostTimeLeftTrainRace(45);
	printf("train=%d\n", CStats::MostTimeLeftTrainRace);
	CStats::RegisterHighestTrainCashEarned(10);
	CStats::RegisterHighestTrainCashEarned(5);
	printf("traincash=%d\n", CStats::HighestTrainCashEarned);
	CStats::RegisterFastestHeliRaceTime(90);
	CStats::RegisterFastestHeliRaceTime(80);
	CStats::RegisterBestHeliRacePosition(3);
	CStats::RegisterBestHeliRacePosition(5);
	printf("heli=%d,%d\n", CStats::FastestHeliRaceTime, CStats::BestHeliRacePosition);
	// PS2 ignores the parameter and counts calls.
	CStats::RegisterHighestGuardianAngelJusticeDished(500);
	CStats::RegisterHighestGuardianAngelJusticeDished(9);
	printf("justice=%d\n", CStats::HighestGuardianAngelJusticeDished);
	CStats::RegisterGuardianAngelLevels(2, 0, 1);
	CStats::RegisterGuardianAngelLevels(1, 3, 0);
	printf("angel=%d,%d,%d\n", CStats::GuardianAngelHighestLevel_Ind, CStats::GuardianAngelHighestLevel_Com,
	       CStats::GuardianAngelHighestLevel_Sub);
	CStats::RegisterBestBanditLapTime(1, 60);
	CStats::RegisterBestBanditLapTime(1, 70);
	CStats::RegisterBestBanditPosition(2, 4);
	CStats::RegisterBestBanditPosition(2, 2);
	CStats::RegisterBestBanditPosition(3, 1);
	CStats::RegisterBestBanditLapTime(-1, 1);
	printf("bandit=%d,%d\n", CStats::BestBanditLapTimes[1], CStats::BestBanditPositions[2]);
	CStats::RegisterStreetRaceFastestTime(5, 100);
	CStats::RegisterStreetRaceFastestTime(5, 90);
	CStats::RegisterStreetRaceFastestLap(0, 30);
	CStats::RegisterStreetRaceBestPosition(5, 2);
	CStats::RegisterStreetRaceBestPosition(6, 1);
	printf("street=%d,%d,%d\n", CStats::StreetRaceFastestTime[5], CStats::StreetRaceFastestLap[0],
	       CStats::StreetRaceBestPosition[5]);
	CStats::RegisterDirtBikeFastestLap(9, 33);
	CStats::RegisterDirtBikeFastestTime(9, 99);
	CStats::RegisterDirtBikeFastestTime(9, 120);
	CStats::RegisterDirtBikeFastestLap(10, 1);
	printf("dirt=%d,%d\n", CStats::DirtBikeFastestLap[9], CStats::DirtBikeFastestTime[9]);
	CStats::RegisterBestTimeGoGoFaggio(65000);
	CStats::RegisterBestTimeGoGoFaggio(70000);
	printf("gogo=%d\n", CStats::BestTimeGoGoFaggio);
	CStats::AddUnlockedCostume(0);
	CStats::AddUnlockedCostume(15);
	CStats::AddUnlockedCostume(16);
	CStats::AddUnlockedCostume(-1);
	printf("costumes=%d\n", CStats::UnlockedCostumes);
}

int main(int argc, char **argv) {
	SCENARIOS_BEGIN
	SCENARIO(roundtrip)
	SCENARIO(old_save)
	SCENARIO(defaults)
	SCENARIO(setters)
	SCENARIOS_END
}
