#!/usr/bin/env python3
"""Exercise the 3DS button-label choice in GetWideStringOfCommandKeys.

Regression test for: "Taking the Peace" printed "Press B" (~k~ ~VEACC~) while
the script's IS_BUTTON_PRESSED(0, 16) check reads physical A, because
CRunningScript::GetPadState maps slot 16 to Circle (A) while player controls
are disabled. See stories/src/core/ControllerConfig.cpp and
stories/src/control/Script5.cpp.
"""
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


class CommandKeyLabels(unittest.TestCase):
    def test_labels(self):
        source = (ROOT / 'stories/src/core/ControllerConfig.cpp').read_text()
        start = source.index('const char *button = action == PED_SNIPER_ZOOM_IN')
        expr = source[start:source.index(';', start) + 1]
        cpp = r'''
#include <cassert>
#include <cstring>
enum { PED_SNIPER_ZOOM_IN, PED_SNIPER_ZOOM_OUT, VEHICLE_ENTER_EXIT, VEHICLE_ACCELERATE, OTHER };
struct CPad {
    int Mode = 0; bool disabled = false;
    bool ArePlayerControlsDisabled() { return disabled; }
    static CPad pad; static CPad *GetPad(int) { return &pad; }
};
CPad CPad::pad;
const char *Nintendo3DSButtons[4][5] = {{"Y", "B", "X", "B", "R"}};
const char *label(int action, bool disabled) {
    CPad::pad.disabled = disabled;
    ''' + expr + r'''
    return button;
}
int main() {
    assert(!strcmp(label(VEHICLE_ACCELERATE, true), "A"));
    assert(!strcmp(label(VEHICLE_ACCELERATE, false), "B"));
    assert(!strcmp(label(VEHICLE_ENTER_EXIT, true), "B"));
    assert(!strcmp(label(VEHICLE_ENTER_EXIT, false), "X"));
    assert(!strcmp(label(OTHER, true), "R"));
}
'''
        with tempfile.TemporaryDirectory(prefix='regta-keylabel-test-') as tmp:
            path, binary = Path(tmp) / 'test.cpp', Path(tmp) / 'test'
            path.write_text(cpp)
            subprocess.run(['c++', '-std=c++11', str(path), '-o', str(binary)], check=True)
            subprocess.run([str(binary)], check=True)


if __name__ == '__main__':
    unittest.main()
