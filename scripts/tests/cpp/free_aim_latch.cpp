// Harness for test_3ds_free_aim_latch.py: CPad::Update3DSFreeAim,
// Is3DSFreeAimActive and Is3DSFreeAimEnteredThisFrame from
// stories/src/core/Pad.cpp are pasted into the CPad stub at the marker below
// (renamed to in-class member definitions).
#include <cassert>
#include <cstdio>

/* The real body references CURMODE (Mode 3 -- remapped Target -- is excluded
 * from latch entry). Match Pad.cpp's simplest definition. */
#define CURMODE (Mode)

struct CCamera {
	static bool m_bUseMouse3rdPerson;
	static bool bFreeCam;
};
bool CCamera::m_bUseMouse3rdPerson = false;
bool CCamera::bFreeCam = false;

/* Stands in for the real TheCamera global: only the one method the latch
 * calls on unlatch is needed, tracked via a call counter. */
struct TheCameraStub {
	int snapBehindCalls = 0;
	void SetCameraDirectlyBehindForFollowPed_CamOnAString() { ++snapBehindCalls; }
};
static TheCameraStub TheCamera;

struct CVehicle {};
struct CPlayerPed {};

static CVehicle *g_vehicle = nullptr;
static CPlayerPed *g_ped = (CPlayerPed *)1;

static CVehicle *FindPlayerVehicle() { return g_vehicle; }
static CPlayerPed *FindPlayerPed() { return g_ped; }

static bool g_canEnter = true, g_canStay = true;
static int g_beginCalls = 0;
static bool Can3DSFreeAim(CPlayerPed *, bool entering) { return entering ? g_canEnter : g_canStay; }
static void Begin3DSFreeAim(CPlayerPed *) { ++g_beginCalls; }

struct ButtonState {
	bool LeftShoulder1 = false;
};

struct CPad {
	int Mode = 0;
	ButtonState NewState;
	ButtonState OldState;
	bool b3DSFreeAimActive = false;
	bool b3DSFreeAimSavedFreeCam = false;
	bool b3DSFreeAimEnteredThisFrame = false;
	bool target = false;

	bool GetTarget() { return target; }

/*@FUNCTIONS@*/
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
	/* Scenario 8: the entry frame is flagged, exactly once. */
	assert(pad.Is3DSFreeAimEnteredThisFrame());

	/* Scenario 5: holding L with no fresh edge does not re-latch after an
	 * unlatch (checked further down); first, hold steady this frame. */
	pad.OldState.LeftShoulder1 = true;
	pad.Update3DSFreeAim();
	assert(pad.Is3DSFreeAimActive());
	assert(!pad.Is3DSFreeAimEnteredThisFrame());

	/* Scenario 2: releasing target unlatches, restores bFreeCam, and snaps
	 * the camera behind the player (PS2-faithful exit). */
	pad.target = false;
	int snapsBefore = TheCamera.snapBehindCalls;
	pad.Update3DSFreeAim();
	assert(!pad.Is3DSFreeAimActive());
	assert(!CCamera::m_bUseMouse3rdPerson);
	assert(!CCamera::bFreeCam);
	assert(TheCamera.snapBehindCalls == snapsBefore + 1);

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
	g_ped = (CPlayerPed *)1;

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

	/* Scenario 7: CURMODE 3 remaps GetTarget() onto LeftShoulder1, so an L
	 * press-edge with GetTarget() true must NOT latch -- otherwise a bare L
	 * tap in that layout would incorrectly enter free aim. */
	CCamera::bFreeCam = false;
	pad.Mode = 3;
	pad.target = true;
	pad.OldState.LeftShoulder1 = false;
	pad.NewState.LeftShoulder1 = true;
	pad.Update3DSFreeAim();
	assert(!pad.Is3DSFreeAimActive());
	assert(!CCamera::m_bUseMouse3rdPerson);
	assert(!CCamera::bFreeCam);

	/* Scenario 9: weapon gate. */
	pad.Mode = 0;
	g_canEnter = false;
	pad.Update3DSFreeAim();
	assert(!pad.Is3DSFreeAimActive());
	g_canEnter = true;
	int begins = g_beginCalls;
	pad.Update3DSFreeAim();
	assert(pad.Is3DSFreeAimActive());
	assert(g_beginCalls == begins + 1);
	g_canStay = false;
	pad.Update3DSFreeAim();
	assert(!pad.Is3DSFreeAimActive());
	g_canStay = true;

	printf("ok\n");
	return 0;
}
