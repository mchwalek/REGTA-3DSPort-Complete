#!/usr/bin/env python3
"""Regression test for the menu helper line on 3DS.

reVC's CMenuManager::DisplayHelperText prints FET_MIG ("LEFT, RIGHT,
MOUSEWHEEL TO ADJUST") and, on the Stats page, FEH_SSA ("CURSORS TO MOVE -
S TO SAVE TO FILE"). Neither key exists in the PS2 disc's ENGLISH.GXT; PS2
draws a button-icon row instead (SLES_541.35 0x345dd8). On 3DS these two
keys must give no text, while FEH_NA still shows. Off 3DS the keys stay as
they were.

Extracts the real GetDefaultHelperTextKey from Frontend.cpp and runs
cpp/menu_helper_text.cpp with and without -D_3DS.
"""
import unittest

from cpptest import between, compile_and_run, harness, read_source


def _source():
    func = between(read_source("stories/src/core/Frontend.cpp"),
                   "static const char *\nGetDefaultHelperTextKey", "\nvoid\nCMenuManager::DisplayHelperText")
    return harness("menu_helper_text.cpp", FUNCTION=func)


class TestMenuHelperText(unittest.TestCase):
    def test_3ds_hides_pc_input_hints(self):
        compile_and_run(_source(), flags=("-D_3DS",))

    def test_pc_keeps_original_hints(self):
        compile_and_run(_source())


if __name__ == "__main__":
    unittest.main()
