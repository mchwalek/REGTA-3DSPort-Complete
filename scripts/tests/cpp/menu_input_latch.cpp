// Harness for test_menu_input_latch.py: CPad::GetWeaponButtonRaw, GetWeapon and
// UpdateWeaponSuppression from stories/src/core/Pad.cpp are pasted in as
// members of the stub CPad at the marker below.
#include <cassert>
#include "scenarios.h"
#define _3DS
struct State { bool Circle = false, Cross = false, RightShoulder1 = false; };
struct CPad {
	int Mode = 0;
	bool IsAffectedByController = true;
	bool disabled = false;
	bool bSuppressWeaponUntilRelease = false;
	State NewState, OldState;
	bool ArePlayerControlsDisabled() { return disabled; }
// CURMODE reads Mode directly for this test; controller-switch detail
// is irrelevant to the suppression latch under test.
#define CURMODE (Mode)
/*@METHODS@*/
};

static void weapon_suppressed_across_menu_close() {
	CPad pad;
	pad.Mode = 0; // Circle slot

	// Player opens a menu (e.g. clothes shop) while holding A/Circle.
	pad.disabled = true;
	pad.NewState.Circle = true;
	pad.UpdateWeaponSuppression();
	assert(pad.bSuppressWeaponUntilRelease);

	// Controls re-enable next frame; button is still physically held.
	pad.disabled = false;
	assert(!pad.GetWeapon());

	// Latch must stay armed across several frames while still held.
	pad.UpdateWeaponSuppression();
	assert(pad.bSuppressWeaponUntilRelease);
	assert(!pad.GetWeapon());
	pad.UpdateWeaponSuppression();
	assert(!pad.GetWeapon());

	// Physical release clears the latch.
	pad.NewState.Circle = false;
	pad.UpdateWeaponSuppression();
	assert(!pad.bSuppressWeaponUntilRelease);

	// A fresh press after release fires normally.
	pad.NewState.Circle = true;
	assert(pad.GetWeapon());
}

static void unaffected_when_never_disabled() {
	CPad pad;
	pad.UpdateWeaponSuppression();
	pad.NewState.Circle = true;
	assert(pad.GetWeapon());
	pad.NewState.Circle = false;
	assert(!pad.GetWeapon());
}

int main(int argc, char **argv) {
	SCENARIOS_BEGIN
	SCENARIO(weapon_suppressed_across_menu_close)
	SCENARIO(unaffected_when_never_disabled)
	SCENARIOS_END
}
