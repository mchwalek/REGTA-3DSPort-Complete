#!/usr/bin/env python3
"""Regression test confirming CMenuManager::AdditionalOptionInput's
MENUPAGE_MAP case (stories/src/core/Frontend.cpp) wires its pan clamps and
horizontal-pan gate through the MAP_PAN_LIMIT_X/_Y and
CAN_PAN_X_AT_CURRENT_ZOOM macros (see test_3ds_map_pan_limit.py for the
macros' own reachability math).

This is a structural check: if any of the five pan-clamp call sites (the
ZOOM macro, the mouse-drag clamp, and the four D-pad/circle-pad edge
checks) or the two horizontal-pan gate call sites regress back to the raw
`m_fMapSize - MENU_X/Y(MAP_MIN_SIZE)` / `m_fMapSize > MENU_X
(MAP_SIZE_TO_ALLOW_X_MOVE)` expressions, this test fails.
"""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
FRONTEND_CPP = ROOT / "stories" / "src" / "core" / "Frontend.cpp"


def extract(source: str, start_marker: str, end_marker: str) -> str:
    start = source.index(start_marker)
    end = source.index(end_marker, start)
    return source[start:end]


class Test3DSMapPanWiring(unittest.TestCase):
    def test_map_enhancements_branch_uses_new_macros(self):
        source = FRONTEND_CPP.read_text()
        # Two regions make up the live (MAP_ENHANCEMENTS-defined) pan/zoom
        # code: the ZOOM macro definition itself, and the switch-case body
        # from the "Adding marker" block through the end of the D-pad
        # edge-pan checks (the next line after it is the shared
        # lastMapTick bookkeeping that runs for every input mode). The gap
        # between these two regions is the `#ifndef MAP_ENHANCEMENTS`
        # legacy movement code, which is dead on 3DS (MAP_ENHANCEMENTS is
        # always defined there) and intentionally untouched by this fix,
        # so it's excluded here rather than polluting the counts below.
        zoom_macro = extract(
            source, "#define ZOOM(x, y, in)", "// Handles Map, Audio and Stats"
        )
        pan_block = extract(
            source,
            "// Adding marker",
            "lastMapTick = CTimer::GetTimeInMillisecondsPauseMode();",
        )
        block = zoom_macro + pan_block

        # Each of the two clamp call sites (ZOOM macro, mouse-drag) uses
        # the macro twice (once per Clamp() bound), and each of the four
        # D-pad edge checks (two X, two Y) uses it once -- 6 total per axis.
        self.assertEqual(block.count("MAP_PAN_LIMIT_X(m_fMapSize)"), 6)
        self.assertEqual(block.count("MAP_PAN_LIMIT_Y(m_fMapSize)"), 6)

        # The two D-pad left/right gates must use the new always-true (on
        # 3DS) gate macro instead of the raw zoom-size comparison.
        self.assertEqual(block.count("CAN_PAN_X_AT_CURRENT_ZOOM"), 2)

        # The old PC-only formulas must be gone from this branch (the PC
        # mouse-wheel use of MAP_SIZE_TO_ALLOW_X_MOVE near the top of this
        # block is untouched and still present exactly once).
        self.assertNotIn("m_fMapSize - MENU_X(MAP_MIN_SIZE)", block)
        self.assertNotIn("m_fMapSize - MENU_Y(MAP_MIN_SIZE)", block)
        self.assertEqual(
            block.count("m_fMapSize > MENU_X(MAP_SIZE_TO_ALLOW_X_MOVE)"), 1
        )


if __name__ == "__main__":
    unittest.main()
