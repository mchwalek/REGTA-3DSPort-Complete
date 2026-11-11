// Harness for test_3ds_command_key_labels.py: the `const char *button = ...;`
// expression from GetWideStringOfCommandKeys in
// stories/src/core/ControllerConfig.cpp is pasted in at the marker below.
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
	/*@EXPR@*/
	return button;
}

int main() {
	assert(!strcmp(label(VEHICLE_ACCELERATE, true), "A"));
	assert(!strcmp(label(VEHICLE_ACCELERATE, false), "B"));
	assert(!strcmp(label(VEHICLE_ENTER_EXIT, true), "B"));
	assert(!strcmp(label(VEHICLE_ENTER_EXIT, false), "X"));
	assert(!strcmp(label(OTHER, true), "R"));
}
