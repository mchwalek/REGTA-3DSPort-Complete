// Harness for test_give_weapon_ammo_cap.py: ClampFiniteAmmo and
// CPed::GiveWeapon (stories/src/peds/Ped.cpp) are pasted in at GIVE_WEAPON.
#include <cassert>
#include <cstdint>
#include "scenarios.h"

typedef int32_t int32;
typedef uint32_t uint32;
typedef uint8_t uint8;

template <typename T> T Min(T a, T b) { return a < b ? a : b; }

enum eWeaponType {
	WEAPONTYPE_UNARMED = 0,
	WEAPONTYPE_COLT45 = 17,
	WEAPONTYPE_SHOTGUN = 19,
	WEAPONTYPE_TEC9 = 22,
	WEAPONTYPE_UZI = 23,
	WEAPONTYPE_M60 = 32,
	WEAPONTYPE_ROCKETLAUNCHER = 30,
	WEAPONTYPE_TOTALWEAPONS = 37,
};
enum eWeaponState { WEAPONSTATE_READY, WEAPONSTATE_FIRING, WEAPONSTATE_RELOADING, WEAPONSTATE_OUT_OF_AMMO };
enum { WEAPONSLOT_SHOTGUN = 4, WEAPONSLOT_SUBMACHINEGUN = 5, WEAPONSLOT_RIFLE = 6 };

struct CWeaponInfo {
	int m_nWeaponSlot;
	int m_nModelId;
	static int32 ms_aMaxAmmoForWeapon[WEAPONTYPE_TOTALWEAPONS];
	static CWeaponInfo *GetWeaponInfo(eWeaponType type) {
		static CWeaponInfo info;
		switch (type) {
		case WEAPONTYPE_COLT45: info.m_nWeaponSlot = 3; break;
		case WEAPONTYPE_SHOTGUN: info.m_nWeaponSlot = 4; break;
		case WEAPONTYPE_TEC9:
		case WEAPONTYPE_UZI: info.m_nWeaponSlot = 5; break;
		case WEAPONTYPE_M60:
		case WEAPONTYPE_ROCKETLAUNCHER: info.m_nWeaponSlot = 7; break;
		default: info.m_nWeaponSlot = 0; break;
		}
		info.m_nModelId = 100 + type;
		return &info;
	}
	static bool IsWeaponSlotAmmoMergeable(uint32 slot) { return slot == WEAPONSLOT_SHOTGUN || slot == WEAPONSLOT_SUBMACHINEGUN || slot == WEAPONSLOT_RIFLE; }
};
// ms_aMaxAmmoForWeapon is -1 for every weapon in the game.
int32 CWeaponInfo::ms_aMaxAmmoForWeapon[WEAPONTYPE_TOTALWEAPONS] = {
	-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
	-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
};

struct CWeapon {
	eWeaponType m_eWeaponType;
	eWeaponState m_eWeaponState;
	int32 m_nAmmoInClip;
	int32 m_nAmmoTotal;
	void Initialise(eWeaponType type, int32 ammo) {
		m_eWeaponType = type;
		m_eWeaponState = WEAPONSTATE_READY;
		m_nAmmoTotal = Min(ammo, 99999);
		m_nAmmoInClip = 0;
	}
	void Shutdown() {
		m_eWeaponType = WEAPONTYPE_UNARMED;
		m_eWeaponState = WEAPONSTATE_READY;
		m_nAmmoInClip = 0;
		m_nAmmoTotal = 0;
	}
	void Reload() {}
};

struct CPed {
	CWeapon m_weapons[10];
	uint8 m_currentWeapon;
	bool bInVehicle;

	CPed() : m_currentWeapon(0), bInVehicle(false) {
		for (int i = 0; i < 10; i++)
			m_weapons[i].Shutdown();
	}
	int GetWeaponSlot(eWeaponType type) { return CWeaponInfo::GetWeaponInfo(type)->m_nWeaponSlot; }
	bool HasWeaponSlot(uint8 slot) { return m_weapons[slot].m_eWeaponType != WEAPONTYPE_UNARMED; }
	CWeapon &GetWeapon(uint8 slot) { return m_weapons[slot]; }
	CWeapon *GetWeapon(void) { return &m_weapons[m_currentWeapon]; }
	void AddWeaponModel(int) {}
	void RemoveWeaponModel(int) {}
	int32 GiveWeapon(eWeaponType weaponType, uint32 ammo, bool unused = true);
};

/*@GIVE_WEAPON@*/

static int32 TotalAfterGive(eWeaponType held, int32 heldAmmo, eWeaponType given, uint32 ammo) {
	CPed ped;
	if (held != WEAPONTYPE_UNARMED)
		ped.GetWeapon(ped.GetWeaponSlot(held)).Initialise(held, heldAmmo);
	int slot = ped.GiveWeapon(given, ammo);
	assert(ped.GetWeapon(slot).m_eWeaponType == given);
	return ped.GetWeapon(slot).m_nAmmoTotal;
}

// PS2 0x1e1180: a same-type total in 10000..29999 becomes 9999.
static void same_type_clamped() {
	assert(TotalAfterGive(WEAPONTYPE_UZI, 6400, WEAPONTYPE_UZI, 6400) == 9999);
	assert(TotalAfterGive(WEAPONTYPE_UZI, 9999, WEAPONTYPE_UZI, 9999) == 9999);
	assert(TotalAfterGive(WEAPONTYPE_UZI, 9999, WEAPONTYPE_UZI, 1) == 9999);
	assert(TotalAfterGive(WEAPONTYPE_UZI, 200, WEAPONTYPE_UZI, 200) == 400);
	assert(TotalAfterGive(WEAPONTYPE_UZI, 5000, WEAPONTYPE_UZI, 4999) == 9999);
}

// 30000 and up is the "infinite" amount (rampages, ATTACH_CHAR_TO_CAR): kept.
static void same_type_infinite_kept() {
	assert(TotalAfterGive(WEAPONTYPE_UZI, 200, WEAPONTYPE_UZI, 30000) == 30200);
	assert(TotalAfterGive(WEAPONTYPE_UZI, 99000, WEAPONTYPE_UZI, 30000) == 99999);
}

// A mergeable slot (shotgun, SMG, rifle) merges the old ammo, then clamps.
static void merged_slot_clamped() {
	assert(TotalAfterGive(WEAPONTYPE_TEC9, 8000, WEAPONTYPE_UZI, 8000) == 9999);
	assert(TotalAfterGive(WEAPONTYPE_TEC9, 200, WEAPONTYPE_UZI, 200) == 400);
	assert(TotalAfterGive(WEAPONTYPE_TEC9, 30000, WEAPONTYPE_UZI, 200) == 30200);
}

// The heavy slot does not merge: the old ammo is dropped.
static void unmerged_slot_replaced() {
	assert(TotalAfterGive(WEAPONTYPE_ROCKETLAUNCHER, 9000, WEAPONTYPE_M60, 9000) == 9000);
}

// A new weapon in an empty slot keeps the amount it was given.
static void empty_slot_kept() {
	assert(TotalAfterGive(WEAPONTYPE_UNARMED, 0, WEAPONTYPE_UZI, 30000) == 30000);
	assert(TotalAfterGive(WEAPONTYPE_UNARMED, 0, WEAPONTYPE_UZI, 15000) == 15000);
}

// Scooter Shooter (TP2) gives the saved SMG ammo back on top of the restored
// SMG, so each attempt doubles it. PS2 stops at 9999, which the HUD still shows.
static void scooter_shooter_doubling_stops_at_9999() {
	CPed ped;
	ped.GetWeapon(WEAPONSLOT_SUBMACHINEGUN).Initialise(WEAPONTYPE_UZI, 200);
	for (int attempt = 0; attempt < 8; attempt++) {
		int32 saved = ped.GetWeapon(WEAPONSLOT_SUBMACHINEGUN).m_nAmmoTotal;
		ped.GiveWeapon(WEAPONTYPE_UZI, saved);
	}
	assert(ped.GetWeapon(WEAPONSLOT_SUBMACHINEGUN).m_nAmmoTotal == 9999);
}

int main(int argc, char **argv) {
	SCENARIOS_BEGIN
	SCENARIO(same_type_clamped)
	SCENARIO(same_type_infinite_kept)
	SCENARIO(merged_slot_clamped)
	SCENARIO(unmerged_slot_replaced)
	SCENARIO(empty_slot_kept)
	SCENARIO(scooter_shooter_doubling_stops_at_9999)
	SCENARIOS_END
}
