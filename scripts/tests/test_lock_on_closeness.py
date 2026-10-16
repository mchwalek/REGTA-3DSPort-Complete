#!/usr/bin/env python3
"""Regression test for the PS2-faithful lock-on target scoring formula used
by CPlayerPed::EvaluateTarget (see
docs/superpowers/specs/2026-10-16-lock-on-ps2-parity-design.md, Design \u00a72
"Scoring").

Extracts the real LockOnCloseness() helper from
stories/src/peds/PlayerPed.cpp, compiles it against a minimal C++ stub, and
asserts:
  - the base formula (-dist - 5*|angle|) with no bonuses
  - each bonus applied alone (+30 priority, +15 on-screen, +40 mission-char)
  - the reported symptom case: a closer on-screen ped outscores a farther
    off-screen one
  - a mission-char ped can outscore a closer ordinary ped
"""
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PLAYERPED_CPP = ROOT / "stories" / "src" / "peds" / "PlayerPed.cpp"


def extract_function(source: str, signature: str) -> str:
    """Extract a verbatim function body starting at `signature`, ending at the
    next column-zero closing brace."""
    start = source.index(signature)
    end = source.index("\n}\n", start) + len("\n}\n")
    return source[start:end]


def build_and_run(cpp_source: str) -> None:
    with tempfile.TemporaryDirectory(prefix="regta-lock-on-closeness-test-") as tmp:
        path = Path(tmp) / "test_lock_on_closeness.cpp"
        binary = Path(tmp) / "test_lock_on_closeness"
        path.write_text(cpp_source)
        subprocess.run(
            ["c++", "-std=c++11", "-fsanitize=address,undefined",
             str(path), "-o", str(binary)],
            check=True,
        )
        subprocess.run([str(binary)], check=True)


class TestLockOnCloseness(unittest.TestCase):
    def test_scoring_formula(self):
        source = PLAYERPED_CPP.read_text()

        fn = extract_function(
            source, "static float\nLockOnCloseness("
        )

        stub = r"""
#include <cassert>
#include <cmath>
#include <cstdio>

/* Abs() is a reLCS-wide inline/macro (common/rwcore or math/general.h);
 * provide the trivial float overload the extracted function needs. */
static inline float Abs(float x) { return x < 0.0f ? -x : x; }

""" + fn + r"""

int main() {
	/* Base formula: 10 m at 0 rad, no bonuses. */
	assert(LockOnCloseness(10.0f, 0.0f, false, false, false) == -10.0f);

	/* Angle term: 10 m at 0.2 rad -> -10 - 5*0.2 = -11. */
	assert(std::fabs(LockOnCloseness(10.0f, 0.2f, false, false, false) - -11.0f) < 1e-5f);
	/* Angle sign doesn't matter (Abs). */
	assert(std::fabs(LockOnCloseness(10.0f, -0.2f, false, false, false) - -11.0f) < 1e-5f);

	/* Each bonus applied alone. */
	assert(std::fabs(LockOnCloseness(10.0f, 0.0f, true, false, false) - 20.0f) < 1e-5f);   // -10 + 30
	assert(std::fabs(LockOnCloseness(10.0f, 0.0f, false, true, false) - 5.0f) < 1e-5f);    // -10 + 15
	assert(std::fabs(LockOnCloseness(10.0f, 0.0f, false, false, true) - 30.0f) < 1e-5f);   // -10 + 40

	/* All bonuses together. */
	assert(std::fabs(LockOnCloseness(10.0f, 0.0f, true, true, true) - 75.0f) < 1e-5f);     // -10 + 30 + 15 + 40

	/* Symptom case: a 12 m on-screen ped outscores a 25 m off-screen ped
	 * (neither priority nor mission-char, both at 0 rad). */
	float nearOnScreen = LockOnCloseness(12.0f, 0.0f, false, true, false);
	float farOffScreen = LockOnCloseness(25.0f, 0.0f, false, false, false);
	assert(nearOnScreen > farOffScreen);

	/* Mission-char bonus can flip a ranking a closer ordinary ped would
	 * otherwise win: 20 m mission-char ped vs 10 m ordinary ped. */
	float missionCharFar = LockOnCloseness(20.0f, 0.0f, false, false, true);
	float ordinaryCloser = LockOnCloseness(10.0f, 0.0f, false, false, false);
	assert(missionCharFar > ordinaryCloser);

	printf("ok\n");
	return 0;
}
"""
        build_and_run(stub)


if __name__ == "__main__":
    unittest.main()
