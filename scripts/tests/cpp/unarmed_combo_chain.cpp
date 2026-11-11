// Harness for test_unarmed_combo_chain.py: ChooseUnarmedComboMove from
// stories/src/peds/PedFight.cpp is pasted in at the marker below.
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

/*@FUNCTION@*/

int main() {
	/* Fresh attack (no combo in progress): A1 with a victim, A2 without. */
	assert(ChooseUnarmedComboMove(FIGHTMOVE_IDLE, false, 0.0f, 0.0f, true) == FIGHTMOVE_COMBO_A1);
	assert(ChooseUnarmedComboMove(FIGHTMOVE_IDLE, false, 0.0f, 0.0f, false) == FIGHTMOVE_COMBO_A2);

	/* PS2 0x1bfb30: a combo move whose association is already gone keeps
	 * chaining as if it were past fo (A -> B, B -> next B). */
	assert(ChooseUnarmedComboMove(FIGHTMOVE_COMBO_A1, false, 0.0f, 0.5f, true) == FIGHTMOVE_COMBO_B1);
	assert(ChooseUnarmedComboMove(FIGHTMOVE_COMBO_A2, false, 0.0f, 0.0f, true) == FIGHTMOVE_COMBO_A3);
	assert(ChooseUnarmedComboMove(FIGHTMOVE_COMBO_B1, false, 0.1f, 0.5f, true) == FIGHTMOVE_COMBO_B2);
	assert(ChooseUnarmedComboMove(FIGHTMOVE_COMBO_B2, false, 1.0f, 0.5f, false) == FIGHTMOVE_COMBO_B3);

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
	/* A1 past fo but fo <= 0: PS2 advances to the next A move. */
	assert(ChooseUnarmedComboMove(FIGHTMOVE_COMBO_A1, true, 0.6f, 0.0f, true) == FIGHTMOVE_COMBO_A2);

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
