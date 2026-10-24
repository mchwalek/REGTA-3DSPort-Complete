#!/usr/bin/env python3
"""CTheZones::GetLevelFromPosition must match PS2 (SLES_541.35 0x2d3b20).

reLCS used to return the first containing map zone's level. Portland and
Staunton zones overlap across the channel, so a boat ("Caught In The Act")
flipped CTheZones::m_CurrLevel back and forth and every flip ran the
blocking island swap with its load screen. PS2 keeps the current level
while any containing zone has it.
"""
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


def function(source, signature):
    start = source.index(signature)
    end = source.index('\n}', start) + 2
    return source[start:end]


class ZoneLevelFromPosition(unittest.TestCase):
    def _run(self, main_body):
        source = (ROOT / 'stories/src/core/Zones.cpp').read_text()
        fn = function(source, 'eLevelName\nCTheZones::GetLevelFromPosition')

        stub = r'''
#include <cassert>
enum eLevelName { LEVEL_GENERIC, LEVEL_INDUSTRIAL, LEVEL_COMMERCIAL, LEVEL_SUBURBAN, LEVEL_UNDERGROUND };
struct CVector { float x, y, z; };
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
static void zone(eLevelName l, float minx, float maxx) {
	CZone z = { minx, -10.0f, -10.0f, maxx, 10.0f, 10.0f, l };
	CTheZones::MapZoneArray[CTheZones::TotalNumberOfMapZones++] = z;
}
static eLevelName at(float x, eLevelName cur) {
	CVector v = { x, 0.0f, 0.0f };
	CGame::currLevel = cur;
	return CTheZones::GetLevelFromPosition(&v);
}
'''
        setup = r'''
	zone(LEVEL_GENERIC, -1000.0f, 1000.0f); // whole map
	zone(LEVEL_COMMERCIAL, 0.0f, 10.0f);
	zone(LEVEL_INDUSTRIAL, 5.0f, 20.0f);
	zone(LEVEL_UNDERGROUND, 15.0f, 30.0f);
	zone(LEVEL_UNDERGROUND, 40.0f, 50.0f);
	zone(LEVEL_SUBURBAN, 45.0f, 60.0f);
'''
        main = 'int main() {\n' + setup + main_body + '\n}\n'
        with tempfile.TemporaryDirectory(prefix='regta-zonelevel-test-') as tmp:
            path, binary = Path(tmp) / 'test.cpp', Path(tmp) / 'test'
            path.write_text(stub + fn + main)
            subprocess.run(['c++', '-std=c++11', '-fsanitize=address,undefined',
                            str(path), '-o', str(binary)], check=True)
            subprocess.run([str(binary)], check=True)

    def test_overlap_keeps_current_level(self):
        # x=7 is in both Staunton and Portland: no swap from either side.
        self._run(r'''
	assert(at(7.0f, LEVEL_COMMERCIAL) == LEVEL_COMMERCIAL);
	assert(at(7.0f, LEVEL_INDUSTRIAL) == LEVEL_INDUSTRIAL);
''')

    def test_overlap_from_elsewhere_takes_last_match(self):
        self._run(r'''
	assert(at(7.0f, LEVEL_SUBURBAN) == LEVEL_INDUSTRIAL);
	assert(at(7.0f, LEVEL_GENERIC) == LEVEL_INDUSTRIAL);
''')

    def test_underground_only_counts_if_first_or_current(self):
        self._run(r'''
	assert(at(17.0f, LEVEL_COMMERCIAL) == LEVEL_INDUSTRIAL);   // level 4 after a match is ignored
	assert(at(17.0f, LEVEL_UNDERGROUND) == LEVEL_UNDERGROUND); // ... unless already underground
	assert(at(25.0f, LEVEL_INDUSTRIAL) == LEVEL_UNDERGROUND);  // only a level-4 zone
	assert(at(47.0f, LEVEL_INDUSTRIAL) == LEVEL_SUBURBAN);     // level 4 first, then a real level
''')

    def test_no_zone_is_generic(self):
        self._run(r'''
	assert(at(35.0f, LEVEL_INDUSTRIAL) == LEVEL_GENERIC);
''')


if __name__ == '__main__':
    unittest.main()
