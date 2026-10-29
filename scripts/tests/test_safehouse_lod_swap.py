#!/usr/bin/env python3
"""Regression test: a swapped-out safehouse shell must not leave its LOD drawn.

main.scm swaps ind_land097 (Toni's Portland building) for TonisAptInterior1.
The shell's LOD (LOD_land097) has dark painted window quads just outside the
interior glass; drawn around the interior they look like a black plane. PS2
swaps the whole sector and never draws that LOD there.

Extracts the real IsLCSBuildingLodSourceSwappedOut from Renderer.cpp and
compiles it with minimal stubs.
"""
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RENDERER_CPP = ROOT / "stories" / "src" / "renderer" / "Renderer.cpp"


def extract(source: str, start_marker: str, end_marker: str) -> str:
    start = source.index(start_marker)
    end = source.index(end_marker, start)
    return source[start:end]


class TestSafehouseLodSwap(unittest.TestCase):
    def test_lod_hidden_only_for_matching_swapped_building(self):
        func = extract(RENDERER_CPP.read_text(), "static bool\nIsLCSBuildingLodSourceSwappedOut", "\n// Reuse bounds")
        program = r"""
#include <cassert>
#define nil nullptr
typedef int int32;
typedef unsigned int uint32;
struct CVector { float x, y, z; CVector operator-(const CVector &o) const { return {x-o.x, y-o.y, z-o.z}; } };
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
""" + func + r"""
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
"""
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "t.cpp"
            exe = Path(tmp) / "t"
            src.write_text(program)
            subprocess.run(["c++", "-std=c++11", str(src), "-o", str(exe)], check=True)
            subprocess.run([str(exe)], check=True)


if __name__ == "__main__":
    unittest.main()
