#!/usr/bin/env python3
"""Regression test for the PS2-faithful unarmed combo-move selection used by
CPed::ChooseAttackPlayer (see docs/superpowers/specs/2026-10-12-melee-lock-on-design.md,
Design \u00a73 "Unarmed combo chaining").

Extracts the real ChooseUnarmedComboMove() function body from
stories/src/peds/PedFight.cpp, compiles it against a minimal C++ stub that
mirrors the real PedFightMoves enum's relative values, and asserts the
decision table:
  - fresh attack (no combo in progress): A1 with a victim, A2 without
  - A1/A2 continuing (t <= comboFollowOnTime): advance to the next A move
  - A1/A2 past comboFollowOnTime with comboFollowOnTime > 0: switch to the
    matching B move
  - B1/B2 within comboFollowOnTime (and comboFollowOnTime > 0): switch back
    to the matching A move
  - B1/B2 otherwise: advance to the next B move
  - a combo move with no live anim association (comboInProgress == False)
    always restarts, even if currentMove is A1/A2/B1/B2
"""
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PEDFIGHT_CPP = ROOT / "stories" / "src" / "peds" / "PedFight.cpp"


def extract_function(source: str, signature: str) -> str:
    """Extract a verbatim function body starting at `signature`, ending at the
    next column-zero closing brace."""
    start = source.index(signature)
    end = source.index("\n}\n", start) + len("\n}\n")
    return source[start:end]


def build_and_run(cpp_source: str) -> None:
    with tempfile.TemporaryDirectory(prefix="regta-combo-chain-test-") as tmp:
        path = Path(tmp) / "test_combo_chain.cpp"
        binary = Path(tmp) / "test_combo_chain"
        path.write_text(cpp_source)
        subprocess.run(
            ["c++", "-std=c++11", "-fsanitize=address,undefined",
             str(path), "-o", str(binary)],
            check=True,
        )
        subprocess.run([str(binary)], check=True)


class TestUnarmedComboChain(unittest.TestCase):
    def test_decision_table(self):
        source = PEDFIGHT_CPP.read_text()

        fn = extract_function(
            source, "static PedFightMoves\nChooseUnarmedComboMove("
        )

        stub = r"""
#include <cassert>
#include <cstdio>

/* Mirrors the real PedFightMoves enum's relative values
 * (stories/src/peds/Ped.h:99-169) for the entries this function touches. */
enum PedFightMoves {
	FIGHTMOVE_NULL,
	FIGHTMOVE_IDLE,
	FIGHTMOVE_SHUFFLE_F,
	FIGHTMOVE_COMBO_A1,
	FIGHTMOVE_COMBO_A2,
	FIGHTMOVE_COMBO_A3,
	FIGHTMOVE_COMBO_B1,
	FIGHTMOVE_COMBO_B2,
	FIGHTMOVE_COMBO_B3,
};

""" + fn + r"""

int main() {
	/* Fresh attack (no combo in progress): A1 with a victim, A2 without. */
	assert(ChooseUnarmedComboMove(FIGHTMOVE_IDLE, false, 0.0f, 0.0f, true) == FIGHTMOVE_COMBO_A1);
	assert(ChooseUnarmedComboMove(FIGHTMOVE_IDLE, false, 0.0f, 0.0f, false) == FIGHTMOVE_COMBO_A2);

	/* A combo move with no live association always restarts, regardless of
	 * which move it was -- comboInProgress gates everything. */
	assert(ChooseUnarmedComboMove(FIGHTMOVE_COMBO_A1, false, 0.0f, 0.5f, true) == FIGHTMOVE_COMBO_A1);
	assert(ChooseUnarmedComboMove(FIGHTMOVE_COMBO_B2, false, 1.0f, 0.5f, false) == FIGHTMOVE_COMBO_A2);

	/* A1 continuing (t <= fo): advance to A2. */
	assert(ChooseUnarmedComboMove(FIGHTMOVE_COMBO_A1, true, 0.4f, 0.5f, true) == FIGHTMOVE_COMBO_A2);
	/* A1 exactly at fo still counts as continuing (t <= fo, not t < fo). */
	assert(ChooseUnarmedComboMove(FIGHTMOVE_COMBO_A1, true, 0.5f, 0.5f, true) == FIGHTMOVE_COMBO_A2);
	/* A1 past fo, fo > 0: switch to the matching B move (A1 -> B1). */
	assert(ChooseUnarmedComboMove(FIGHTMOVE_COMBO_A1, true, 0.6f, 0.5f, true) == FIGHTMOVE_COMBO_B1);
	/* A2 continuing: advance to A3. */
	assert(ChooseUnarmedComboMove(FIGHTMOVE_COMBO_A2, true, 0.4f, 0.5f, true) == FIGHTMOVE_COMBO_A3);
	/* A2 past fo, fo > 0: switch to B2. */
	assert(ChooseUnarmedComboMove(FIGHTMOVE_COMBO_A2, true, 0.6f, 0.5f, true) == FIGHTMOVE_COMBO_B2);
	/* A1 past fo but fo <= 0 (move has no follow-on window at all):
	 * restarts instead of switching to B (no combo signal to act on). */
	assert(ChooseUnarmedComboMove(FIGHTMOVE_COMBO_A1, true, 0.6f, 0.0f, true) == FIGHTMOVE_COMBO_A1);

	/* B1 within fo, fo > 0: switch back to A1. */
	assert(ChooseUnarmedComboMove(FIGHTMOVE_COMBO_B1, true, 0.4f, 0.5f, true) == FIGHTMOVE_COMBO_A1);
	/* B1 past fo: advance to B2. */
	assert(ChooseUnarmedComboMove(FIGHTMOVE_COMBO_B1, true, 0.6f, 0.5f, true) == FIGHTMOVE_COMBO_B2);
	/* B1 with fo <= 0: advance to B2 (no switch-back signal). */
	assert(ChooseUnarmedComboMove(FIGHTMOVE_COMBO_B1, true, 0.1f, 0.0f, true) == FIGHTMOVE_COMBO_B2);
	/* B2 within fo, fo > 0: switch back to A2. */
	assert(ChooseUnarmedComboMove(FIGHTMOVE_COMBO_B2, true, 0.4f, 0.5f, true) == FIGHTMOVE_COMBO_A2);
	/* B2 past fo: advance to B3. */
	assert(ChooseUnarmedComboMove(FIGHTMOVE_COMBO_B2, true, 0.6f, 0.5f, true) == FIGHTMOVE_COMBO_B3);

	/* A3/B3 (combo finishers) are not in the switch -- always restart. */
	assert(ChooseUnarmedComboMove(FIGHTMOVE_COMBO_A3, true, 0.1f, 0.5f, true) == FIGHTMOVE_COMBO_A1);
	assert(ChooseUnarmedComboMove(FIGHTMOVE_COMBO_B3, true, 0.1f, 0.5f, false) == FIGHTMOVE_COMBO_A2);

	printf("ok\n");
	return 0;
}
"""
        build_and_run(stub)


if __name__ == "__main__":
    unittest.main()
