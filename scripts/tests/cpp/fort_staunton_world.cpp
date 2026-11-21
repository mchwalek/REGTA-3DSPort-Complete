// Harness for test_fort_staunton_construction_set.py: SyncLCSFortStauntonWorld
// from stories/src/control/Script9.cpp is pasted in at the marker below.
#include "stubs.h"

struct CTheScripts {
	static int FSDestroyedFlag;
	static bool destroyed;
	static bool IsFortStauntonDestroyed() { return destroyed; }
};
int CTheScripts::FSDestroyedFlag = 4512;
bool CTheScripts::destroyed = false;

struct CFileLoader {
	static const char *loadedScene;
	static void LoadScene(const char *path) { loadedScene = path; }
};
const char *CFileLoader::loadedScene = nil;

struct Range { int32 first, last; };
static Range removed[16];
static int numRemoved;
static int collisionPhase = -1;

static void RemoveBuildingsInModelRange(int32 firstModel, int32 lastModel)
{
	assert(numRemoved < 16);
	removed[numRemoved++] = {firstModel, lastModel};
}

static void LoadLCSFortCollision(bool destroyed) { collisionPhase = destroyed; }

static int32 gLCSFortStauntonState = -1;

/*@FUNCTION@*/

static void Reset(bool destroyed)
{
	numRemoved = 0;
	collisionPhase = -1;
	CFileLoader::loadedScene = nil;
	CTheScripts::destroyed = destroyed;
	gLCSFortStauntonState = -1;
}

static bool AnyRemovedModel(int32 first, int32 last)
{
	for(int i = 0; i < numRemoved; i++)
		if(removed[i].first <= last && removed[i].last >= first)
			return true;
	return false;
}

static bool RemovedRange(int32 first, int32 last)
{
	for(int i = 0; i < numRemoved; i++)
		if(removed[i].first == first && removed[i].last == last)
			return true;
	return false;
}

int main()
{
	// Intact fort: the construction set (3653..3660) is a PS2 static
	// building set and must stay. The destroyed models (3685..3741) go.
	Reset(false);
	SyncLCSFortStauntonWorld();
	assert(collisionPhase == 0);
	assert(!AnyRemovedModel(3653, 3660));
	assert(RemovedRange(3685, 3741));
	assert(CFileLoader::loadedScene == nil);

	// Destroyed fort: the intact models go, the construction set stays.
	Reset(true);
	SyncLCSFortStauntonWorld();
	assert(collisionPhase == 1);
	assert(!AnyRemovedModel(3653, 3660));
	assert(RemovedRange(3600, 3652));
	assert(RemovedRange(3661, 3664));
	assert(CFileLoader::loadedScene && strcmp(CFileLoader::loadedScene, "DATA/Maps/fortdestroyed.ipl") == 0);
	return 0;
}
