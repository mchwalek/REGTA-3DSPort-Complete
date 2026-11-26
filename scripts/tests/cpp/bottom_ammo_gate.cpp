// Harness for test_3ds_bottom_ammo_gate.py: ShouldDrawAmmo3DS from
// stories/src/core/BottomScreen3DS.cpp is pasted in at the marker below.
#include "stubs.h"
#include "scenarios.h"

enum eWeaponType { WEAPONTYPE_UNARMED, WEAPONTYPE_BASEBALLBAT, WEAPONTYPE_COLT45 = 10, WEAPONTYPE_UZI = 22, WEAPONTYPE_DETONATOR = 34 };
struct CWeapon {
	eWeaponType m_eWeaponType;
	int32 m_nAmmoInClip;
	int32 m_nAmmoTotal;
};
struct CWeaponInfo {
	int32 m_nWeaponSlot;
};
struct CDarkel {
	static bool frenzy;
	static bool FrenzyOnGoing() { return frenzy; }
};
bool CDarkel::frenzy = false;

/*@FUNCTION@*/

static bool
Gate(eWeaponType type, int32 slot, int32 total, int32 clip)
{
	CWeapon weapon = { type, clip, total };
	CWeaponInfo info = { slot };
	return ShouldDrawAmmo3DS(&weapon, &info);
}

static void normal_reserve_draws() { assert(Gate(WEAPONTYPE_UZI, 5, 130, 30)); }
static void reserve_9998_draws() { assert(Gate(WEAPONTYPE_UZI, 5, 9998 + 30, 30)); }
static void reserve_9999_hides() { assert(!Gate(WEAPONTYPE_UZI, 5, 9999 + 30, 30)); }
static void attach_30000_hides() { assert(!Gate(WEAPONTYPE_UZI, 5, 30000, 100)); }
static void empty_clip_30000_hides() { assert(!Gate(WEAPONTYPE_UZI, 5, 30000, 0)); }
static void rampage_hides()
{
	CDarkel::frenzy = true;
	assert(!Gate(WEAPONTYPE_UZI, 5, 130, 30));
	CDarkel::frenzy = false;
}
static void melee_slot_hides() { assert(!Gate(WEAPONTYPE_BASEBALLBAT, 1, 1, 0)); }
static void detonator_hides() { assert(!Gate(WEAPONTYPE_DETONATOR, 8, 1, 1)); }

int main(int argc, char **argv)
{
	SCENARIOS_BEGIN
	SCENARIO(normal_reserve_draws)
	SCENARIO(reserve_9998_draws)
	SCENARIO(reserve_9999_hides)
	SCENARIO(attach_30000_hides)
	SCENARIO(empty_clip_30000_hides)
	SCENARIO(rampage_hides)
	SCENARIO(melee_slot_hides)
	SCENARIO(detonator_hides)
	SCENARIOS_END
}
