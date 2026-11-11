#!/usr/bin/env python3
"""Exercise the 3DS button-label choice in GetWideStringOfCommandKeys.

Regression test for: "Taking the Peace" printed "Press B" (~k~ ~VEACC~) while
the script's IS_BUTTON_PRESSED(0, 16) check reads physical A, because
CRunningScript::GetPadState maps slot 16 to Circle (A) while player controls
are disabled. See stories/src/core/ControllerConfig.cpp and
stories/src/control/Script5.cpp.
"""
import unittest

from cpptest import between, compile_and_run, harness, read_source


class CommandKeyLabels(unittest.TestCase):
    def test_labels(self):
        expr = between(read_source('stories/src/core/ControllerConfig.cpp'),
                       'const char *button = action == PED_SNIPER_ZOOM_IN', ';', include_end=True)
        compile_and_run(harness('command_key_labels.cpp', EXPR=expr), sanitize=False)


if __name__ == '__main__':
    unittest.main()
