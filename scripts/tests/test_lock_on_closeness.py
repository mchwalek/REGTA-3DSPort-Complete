#!/usr/bin/env python3
"""Regression test for the PS2-faithful lock-on target scoring formula used
by CPlayerPed::EvaluateTarget (see
docs/superpowers/specs/2026-10-16-lock-on-ps2-parity-design.md, Design \u00a72
"Scoring").

Extracts the real LockOnCloseness() helper from
stories/src/peds/PlayerPed.cpp, compiles it into cpp/lock_on_closeness.cpp,
and asserts:
  - the base formula (-dist - 5*|angle|) with no bonuses
  - each bonus applied alone (+30 priority, +15 on-screen, +40 mission-char)
  - the reported symptom case: a closer on-screen ped outscores a farther
    off-screen one
  - a mission-char ped can outscore a closer ordinary ped
"""
import unittest

from cpptest import compile_and_run, extract_function, harness, read_source


class TestLockOnCloseness(unittest.TestCase):
    def test_scoring_formula(self):
        fn = extract_function(read_source("stories/src/peds/PlayerPed.cpp"), "static float\nLockOnCloseness(")
        out = compile_and_run(harness("lock_on_closeness.cpp", FUNCTION=fn))
        self.assertEqual(out.strip(), "ok")


if __name__ == "__main__":
    unittest.main()
