// Harness for test_safehouse_lod_swap.py: IsLCSBuildingLodSourceSwappedOut
// from stories/src/renderer/Renderer.cpp is pasted in at the marker below.
#include "stubs.h"

struct CEntity {
	CVector pos; bool touching;
	const CVector &GetPosition() const { return pos; }
	bool GetIsTouching(CEntity *) const { return touching; }
};
struct CBuilding : CEntity {};
struct CSimpleModelInfo {};
CSimpleModelInfo models[3];
struct CModelInfo { static CSimpleModelInfo *GetModelInfo(int32 i) { return &models[i]; } };
enum { MAX_NUM_BUILDING_SWAPS = 4 };
struct tBuildingSwap { CBuilding *m_pBuilding; int32 m_nNewModel; int32 m_nOldModel; uint32 m_nPoolType, m_nPoolHandle; };
struct CTheScripts { static tBuildingSwap BuildingSwapArray[MAX_NUM_BUILDING_SWAPS]; };
tBuildingSwap CTheScripts::BuildingSwapArray[MAX_NUM_BUILDING_SWAPS];

/*@FUNCTION@*/

int main()
{
	CEntity lod{{0.0f, 0.0f, 0.0f}, false};
	CBuilding shell; shell.pos = {0.5f, 0.5f, 10.0f}; shell.touching = false;
	CBuilding far; far.pos = {500.0f, 0.0f, 0.0f}; far.touching = false;
	assert(!IsLCSBuildingLodSourceSwappedOut(&lod, &models[1]));
	CTheScripts::BuildingSwapArray[2] = {&far, 2, 1, 0, 0};
	assert(!IsLCSBuildingLodSourceSwappedOut(&lod, &models[1]));
	CTheScripts::BuildingSwapArray[3] = {&shell, 2, 0, 0, 0};
	assert(!IsLCSBuildingLodSourceSwappedOut(&lod, &models[1]));
	CTheScripts::BuildingSwapArray[1] = {&shell, 2, 1, 0, 0};
	assert(IsLCSBuildingLodSourceSwappedOut(&lod, &models[1]));
	return 0;
}
