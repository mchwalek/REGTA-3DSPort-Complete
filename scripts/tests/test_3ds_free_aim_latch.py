#!/usr/bin/env python3
"""Regression test for the 3DS third-person free-aim latch (CPad::Update3DSFreeAim).

Extracts the real function bodies from stories/src/core/Pad.cpp, compiles them
against a minimal C++ stub, and asserts the latch's enter/exit state machine:
  1. tap L while targeting -> latches
  2. releasing target -> unlatches, restores bFreeCam
  3. entering a vehicle -> unlatches
  4. player ped gone -> unlatches
  5. holding L with no fresh press-edge -> does not re-latch
  6. CCamera::bFreeCam save/restore is correct when the user's Free Cam
     option was already on before latching
"""
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PAD_CPP = ROOT / "stories" / "src" / "core" / "Pad.cpp"


def extract_function(source: str, signature: str) -> str:
    """Extract a verbatim function body starting at `signature`, ending at the
    next column-zero closing brace."""
    start = source.index(signature)
    end = source.index("\n}\n", start) + len("\n}\n")
    return source[start:end]


def build_and_run(cpp_source: str) -> None:
    with tempfile.TemporaryDirectory(prefix="regta-free-aim-test-") as tmp:
        path = Path(tmp) / "test_free_aim_latch.cpp"
        binary = Path(tmp) / "test_free_aim_latch"
        path.write_text(cpp_source)
        subprocess.run(
            ["c++", "-std=c++11", "-fsanitize=address,undefined",
             str(path), "-o", str(binary)],
            check=True,
        )
        subprocess.run([str(binary)], check=True)


class Test3DSFreeAimLatch(unittest.TestCase):
    def test_latch_state_machine(self):
        source = PAD_CPP.read_text()

        update_fn = extract_function(source, "void\nCPad::Update3DSFreeAim()")
        update_fn = update_fn.replace(
            "void\nCPad::Update3DSFreeAim()", "void Update3DSFreeAim()"
        )

        active_fn = extract_function(source, "bool\nCPad::Is3DSFreeAimActive()")
        active_fn = active_fn.replace(
            "bool\nCPad::Is3DSFreeAimActive()", "bool Is3DSFreeAimActive()"
        )

        # The real function body references the CURMODE macro (added by
        # Task 1's fix round to exclude Mode 3 -- the remapped-Target
        # controller layout -- from latch entry). Match Pad.cpp's simplest
        # definition: CURMODE (Mode).
        stub = r"""
#include <cassert>
#include <cstdio>

#define CURMODE (Mode)

struct CCamera {
	static bool m_bUseMouse3rdPerson;
	static bool bFreeCam;
};
bool CCamera::m_bUseMouse3rdPerson = false;
bool CCamera::bFreeCam = false;

struct CVehicle {};
struct CPed {};

static CVehicle *g_vehicle = nullptr;
static CPed *g_ped = (CPed *)1;

static CVehicle *FindPlayerVehicle() { return g_vehicle; }
static CPed *FindPlayerPed() { return g_ped; }

struct ButtonState {
	bool LeftShoulder1 = false;
};

struct CPad {
	int Mode = 0;
	ButtonState NewState;
	ButtonState OldState;
	bool b3DSFreeAimActive = false;
	bool b3DSFreeAimSavedFreeCam = false;
	bool target = false;

	bool GetTarget() { return target; }

""" + update_fn + "\n\n" + active_fn + r"""
};

int main() {
	CPad pad;
	pad.Mode = 0; /* Mode != 3, so the CURMODE guard permits latching. */

	/* Scenario 1: tap L while targeting -> latches. */
	pad.target = true;
	pad.NewState.LeftShoulder1 = true;
	pad.OldState.LeftShoulder1 = false;
	pad.Update3DSFreeAim();
	assert(pad.Is3DSFreeAimActive());
	assert(CCamera::m_bUseMouse3rdPerson);
	assert(CCamera::bFreeCam);

	/* Scenario 5: holding L with no fresh edge does not re-latch after an
	 * unlatch (checked further down); first, hold steady this frame. */
	pad.OldState.LeftShoulder1 = true;
	pad.Update3DSFreeAim();
	assert(pad.Is3DSFreeAimActive());

	/* Scenario 2: releasing target unlatches and restores bFreeCam. */
	pad.target = false;
	pad.Update3DSFreeAim();
	assert(!pad.Is3DSFreeAimActive());
	assert(!CCamera::m_bUseMouse3rdPerson);
	assert(!CCamera::bFreeCam);

	/* Scenario 5 continued: L is still held (no release/re-press edge);
	 * re-targeting must NOT re-latch. */
	pad.target = true;
	pad.Update3DSFreeAim();
	assert(!pad.Is3DSFreeAimActive());

	/* Release and re-press L to get a fresh edge, then re-latch. */
	pad.NewState.LeftShoulder1 = false;
	pad.OldState.LeftShoulder1 = true;
	pad.Update3DSFreeAim();
	pad.OldState.LeftShoulder1 = false;
	pad.NewState.LeftShoulder1 = true;
	pad.Update3DSFreeAim();
	assert(pad.Is3DSFreeAimActive());

	/* Scenario 3: entering a vehicle unlatches. */
	g_vehicle = (CVehicle *)1;
	pad.Update3DSFreeAim();
	assert(!pad.Is3DSFreeAimActive());
	g_vehicle = nullptr;

	/* Re-latch, then scenario 4: player ped gone unlatches. */
	pad.OldState.LeftShoulder1 = false;
	pad.NewState.LeftShoulder1 = true;
	pad.Update3DSFreeAim();
	assert(pad.Is3DSFreeAimActive());
	g_ped = nullptr;
	pad.Update3DSFreeAim();
	assert(!pad.Is3DSFreeAimActive());
	g_ped = (CPed *)1;

	/* Scenario 6: bFreeCam save/restore -- if bFreeCam was already true
	 * before latching (e.g. user's Free Cam option), it must still read
	 * true after unlatching, not be force-cleared. */
	CCamera::bFreeCam = true;
	pad.target = true;
	pad.OldState.LeftShoulder1 = false;
	pad.NewState.LeftShoulder1 = true;
	pad.Update3DSFreeAim();
	assert(pad.Is3DSFreeAimActive());
	assert(CCamera::bFreeCam);
	pad.target = false;
	pad.Update3DSFreeAim();
	assert(!pad.Is3DSFreeAimActive());
	assert(CCamera::bFreeCam);

	printf("ok\n");
	return 0;
}
"""
        build_and_run(stub)


if __name__ == "__main__":
    unittest.main()
