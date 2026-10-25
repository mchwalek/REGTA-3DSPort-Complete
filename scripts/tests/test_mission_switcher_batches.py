#!/usr/bin/env python3
"""Compile the real debug-menu mission-batch stepping (L/R) against host stubs."""
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


def function(source, signature):
    start = source.index(signature)
    end = source.index('\n}', start) + 2
    return source[start:end]


class MissionSwitcherBatches(unittest.TestCase):
    def test_batch_stepping(self):
        source = (ROOT / 'stories/src/core/re3.cpp').read_text()
        fns = '\n'.join(function(source, sig) for sig in (
            'static bool\nSameMissionBatch(',
            'static int32\nMissionBatchStart(',
            'static int32\nStepMissionBatch('))
        start = source.index('static const char* missions[] = {')
        missions = source[start:source.index('};', start) + 2]

        cpp = r'''
#include <cassert>
#include <cstring>
typedef int int32;
#define nil nullptr
''' + fns + '\n' + missions + r'''
static int32 find(const char *name) {
 for(int32 i = 0; i < (int32)(sizeof(missions)/sizeof(missions[0])); i++)
  if(strcmp(missions[i], name) == 0) return i;
 assert(!"missing"); return -1;
}
int main() {
 const int32 n = sizeof(missions)/sizeof(missions[0]);
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
'''
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / 't.cpp'
            exe = Path(tmp) / 't'
            src.write_text(cpp)
            subprocess.run(['c++', '-std=c++11', str(src), '-o', str(exe)], check=True)
            subprocess.run([str(exe)], check=True)


if __name__ == '__main__':
    unittest.main()
