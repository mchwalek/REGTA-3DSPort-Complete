// Harness for test_lcs_stats_lines.py: CStats::ConstructStatLine
// (stories/src/core/Stats.cpp) is pasted in at FUNCTION, the CStats class from
// Stats.h at CLASS and its static member definitions at STATICS.
// `./test <scenario>` prints one row per line as "<left key>|<right text>".
#include "stubs.h"
#include "scenarios.h"
#include <climits>
#include <string>

#define FIX_BUGS
#define USE_MEASUREMENTS_IN_METERS
#define USE_PRECISE_MEASUREMENT_CONVERTION
#define Const const
#define MILES_IN_METER 0.000621371192f
#define FEET_IN_METER 3.28084f

/*@ENUMS@*/

/*@CLASS@*/

/*@STATICS@*/

static wchar gUString[256], gUString2[256];
static std::string gLeft;
static std::string gRight;
static int gIndent;

static void UnicodeStrcpy(wchar *dst, const wchar *src) {
	while ((*dst++ = *src++)) {}
}
static std::string Narrow(const wchar *s) {
	std::string out;
	for (; *s; s++) out += (char)*s;
	return out;
}
static float Floor(float f) { return floorf(f); }

struct CText {
	wchar buf[8][64];
	int next;
	wchar *Get(const char *key) {
		wchar *out = buf[next++ % 8];
		int i = 0;
		for (; key[i]; i++) out[i] = key[i];
		out[i] = 0;
		return out;
	}
} TheText;

struct CTimer {
	static uint32 GetTimeInMilliseconds() { return 3723000; }
};
struct CGame {
	static bool nastyGame;
};
bool CGame::nastyGame;
struct CPlayerInfo {
	int32 m_nCollectedPackages;
	int32 m_nTotalPackages;
};
struct CWorld {
	static CPlayerInfo Players[1];
	static int PlayerInFocus;
};
CPlayerInfo CWorld::Players[1];
int CWorld::PlayerInFocus;
struct CMenuManager {
	enum LANGUAGE { LANGUAGE_AMERICAN, LANGUAGE_FRENCH, LANGUAGE_GERMAN, LANGUAGE_ITALIAN, LANGUAGE_SPANISH };
	int m_PrefsLanguage;
} FrontEndMenuManager;
static float gListenTime[NUM_RADIOS];
struct cDMAudio {
	float *GetListenTimeArray() { return gListenTime; }
} DMAudio;
struct CFont {
	static bool IsJapanese() { return false; }
};

// Types 1 and 3 are floats, the others ints (see CStats::BuildStatLine).
static std::string Value(void *p, int type) {
	char s[32];
	if (type == 1 || type == 3)
		snprintf(s, sizeof(s), "%g", *(float *)p);
	else
		snprintf(s, sizeof(s), "%d", *(int *)p);
	return s;
}
void CStats::BuildStatLine(const char *text, void *stat, int type, void *stat2, int, int indent) {
	gLeft = text;
	gIndent = indent;
	gRight = stat ? Value(stat, type) : "";
	if (stat2) gRight += "/" + Value(stat2, 0);
}
wchar *CStats::FindChaseString(float) { return TheText.Get("CHASE_STRING"); }
float CStats::GetPercentageProgress() { return 0.0f; }

/*@FUNCTION@*/

static void PrintRows() {
	int total = CStats::ConstructStatLine(99999);
	for (int i = 0; i < total; i++) {
		gLeft = "?";
		gRight.clear();
		gIndent = 0;
		gUString[0] = gUString2[0] = 0;
		CStats::ConstructStatLine(i);
		// TEXT_ON_RIGHT clears gUString and fills gUString2 without BuildStatLine.
		if (gUString[0] == 0 && gUString2[0] != 0) {
			gLeft = "";
			gRight = Narrow(gUString2);
		}
		printf("%s|%s|%d\n", gLeft.c_str(), gRight.c_str(), gIndent);
	}
}

// The PS2 start values of the race positions: INT_MAX, no race finished.
static void NoRacesFinished() {
	CStats::BestHeliRacePosition = INT_MAX;
	for (int i = 0; i < CStats::TOTAL_BANDIT_RACES; i++) CStats::BestBanditPositions[i] = INT_MAX;
	for (int i = 0; i < CStats::TOTAL_STREET_RACES; i++) CStats::StreetRaceBestPosition[i] = INT_MAX;
}

static void zero() {
	CStats::BestStuntJump = 0;
	CStats::BestPositions[0] = INT_MAX;
	NoRacesFinished();
	PrintRows();
}

// Every counter set. Gang 9 has the most kills, so it is the least favourite gang.
static void full() {
	CGame::nastyGame = true;
	CWorld::Players[0].m_nTotalPackages = 100;
	CStats::NumberKillFrenziesPassed = 1;
	CStats::PedsKilledOfThisType[PEDTYPE_GANG1] = 3;
	CStats::PedsKilledOfThisType[PEDTYPE_GANG9] = 7;
	CStats::BestStuntJump = 3;
	CStats::LoanSharks = 1;
	CStats::CriminalsCaught = 1;
	CStats::HighestLevelVigilanteMission = 1;
	CStats::PassengersDroppedOffWithTaxi = 1;
	CStats::MoneyMadeWithTaxi = 1;
	CStats::LivesSavedWithAmbulance = 1;
	CStats::HighestLevelAmbulanceMission = 1;
	CStats::FiresExtinguished = 1;
	CStats::HighestLevelFireMission = 1;
	CStats::StoresKnockedOff = 1;
	CStats::MovieStunts = 1;
	CStats::Assassinations = 1;
	CStats::PhotosTaken = 1;
	CStats::PizzasDelivered = 1;
	CStats::GarbagePickups = 1;
	CStats::IceCreamSold = 1;
	CStats::BestPositions[0] = INT_MAX;
	CStats::FlightTime = 2 * 60 * 60000;
	CStats::BloodRingKills = 1;
	CStats::BloodRingTime = 1;
	CStats::SeagullsKilled = 1;
	CStats::FashionBudget = 1;
	CStats::PropertyBudget = 2;
	gListenTime[9] = 5.0f;
	gListenTime[0] = 1.0f;
	for (int i = 1; i < 9; i++) gListenTime[i] = 2.0f;
	gListenTime[10] = 0.0f;
	NoRacesFinished();
	CStats::HitmenKilled = 1;
	CStats::CarsSold = 1;
	CStats::MoneyMadeWithCarSales = 1;
	CStats::BikesSold = 1;
	CStats::MoneyMadeWithBikeSales = 1;
	CStats::NumberOfExportedCars = 1;
	CStats::TotalNumberOfCarExport = 3;
	CStats::HighestLevelSlashTv = 1;
	CStats::MoneyMadeWithSlashTv = 1;
	CStats::TotalKillsOnSlashTV = 1;
	CStats::MoneyMadeCollectingTrash = 1;
	CStats::GuardianAngelMissionsPassed = 1;
	CStats::HighestGuardianAngelJusticeDished = 1;
	CStats::GuardianAngelHighestLevel_Com = 1;
	CStats::MostTimeLeftTrainRace = 125;
	CStats::BestHeliRacePosition = 2;
	CStats::BestBanditPositions[1] = 1;
	CStats::BestBanditLapTimes[1] = 61;
	CStats::StreetRaceBestPosition[2] = 1;
	CStats::StreetRaceFastestLap[2] = 30;
	CStats::StreetRaceFastestTime[2] = 90;
	CStats::DirtBikeFastestLap[0] = 40;
	CStats::DirtBikeFastestTime[0] = 120;
	CStats::DirtBikeMostAir = 1;
	CStats::BestTimeGoGoFaggio = 65000;
	CStats::NoodlesDelivered = 1;
	CStats::MoneyMadeFromTourist = 1;
	CStats::TouristsTakenToSpots = 1;
	CStats::TopScrapyardChallengeScore = 1;
	CStats::Top9mmMayhemScore = 1;
	CStats::TopScooterShooterScore = 1;
	CStats::TopWichitaWipeoutScore = 1;
	CStats::MaxSecondsOnCarnageLeft = 1;
	CStats::MaxKillsOnRcTriad = 1;
	CStats::UnlockedCostumes = 1 << 0 | 1 << 15;
	CStats::SessionStartTime = 2 * 60000;
	PrintRows();
}

// Every race finished. The air time row needs a finished dirt bike race.
static void races() {
	CStats::BestPositions[0] = INT_MAX;
	for (int i = 0; i < CStats::TOTAL_BANDIT_RACES; i++) CStats::BestBanditPositions[i] = 1;
	for (int i = 0; i < CStats::TOTAL_STREET_RACES; i++) CStats::StreetRaceBestPosition[i] = 1;
	for (int i = 0; i < CStats::TOTAL_DIRT_BIKE_RACES; i++) CStats::DirtBikeFastestLap[i] = 1;
	CStats::BestHeliRacePosition = INT_MAX;
	CStats::DirtBikeMostAir = 1;
	PrintRows();
}

// Air time without a finished dirt bike race is not listed.
static void air_only() {
	CStats::BestPositions[0] = INT_MAX;
	NoRacesFinished();
	CStats::DirtBikeMostAir = 1;
	PrintRows();
}

// ST_DAMA ("Property destroyed") shows PropertyDestroyed, not PropertyBudget.
static void damage() {
	CStats::PropertyDestroyed = 1234;
	CStats::PropertyBudget = 99;
	CStats::BestPositions[0] = INT_MAX;
	for (int i = 0; i <= 99999; i++) {
		if (CStats::ConstructStatLine(i) != 0) break;
		if (gLeft == "ST_DAMA") {
			printf("ST_DAMA=%s\n", gRight.c_str());
			return;
		}
	}
	printf("ST_DAMA missing\n");
}

int main(int argc, char **argv) {
	SCENARIOS_BEGIN
	SCENARIO(zero)
	SCENARIO(full)
	SCENARIO(damage)
	SCENARIO(races)
	SCENARIO(air_only)
	SCENARIOS_END
}
