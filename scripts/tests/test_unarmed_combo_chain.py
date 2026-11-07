#!/usr/bin/env python3
"""Regression test for the PS2-faithful unarmed combo-move selection used by
CPed::ChooseAttackPlayer (see docs/superpowers/specs/2026-10-12-melee-lock-on-design.md,
Design \u00a73 "Unarmed combo chaining").

Extracts the real ChooseUnarmedComboMove() function body from
stories/src/peds/PedFight.cpp, compiles it into cpp/unarmed_combo_chain.cpp
(a stub that mirrors the real PedFightMoves enum's relative values), and
asserts the decision table:
  - fresh attack (no combo in progress): A1 with a victim, A2 without
  - A1/A2 continuing (t <= comboFollowOnTime): advance to the next A move
  - A1/A2 past comboFollowOnTime with comboFollowOnTime > 0: switch to the
    matching B move
  - B1/B2 within comboFollowOnTime (and comboFollowOnTime > 0): switch back
    to the matching A move
  - B1/B2 otherwise: advance to the next B move
  - a combo move with no live anim association keeps chaining as if past
    comboFollowOnTime (PS2 SLES_541.35 0x1bfb30)
"""
import unittest

from cpptest import compile_and_run, extract_function, harness, read_source


class TestUnarmedComboChain(unittest.TestCase):
    def test_decision_table(self):
        fn = extract_function(read_source("stories/src/peds/PedFight.cpp"), "static PedFightMoves\nChooseUnarmedComboMove(")
        out = compile_and_run(harness("unarmed_combo_chain.cpp", FUNCTION=fn))
        self.assertEqual(out.strip(), "ok")


if __name__ == "__main__":
    unittest.main()
