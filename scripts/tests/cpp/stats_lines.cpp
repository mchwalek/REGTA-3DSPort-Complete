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
void CStats::BuildStatLine(const char *text, void *stat, int type, void *stat2, int) {
	gLeft = text;
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
		gUString[0] = gUString2[0] = 0;
		CStats::ConstructStatLine(i);
		// TEXT_ON_RIGHT clears gUString and fills gUString2 without BuildStatLine.
		if (gUString[0] == 0 && gUString2[0] != 0) {
			gLeft = "";
			gRight = Narrow(gUString2);
		}
		printf("%s|%s\n", gLeft.c_str(), gRight.c_str());
	}
}

static void zero() {
	CStats::BestStuntJump = 0;
	CStats::BestPositions[0] = INT_MAX;
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
	SCENARIOS_END
}
