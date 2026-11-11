// Harness for test_lcs_script_sound_ids.py: host mirror of CWeapon's layout
// (stories/src/weapons/Weapon.h) pinning that m_nChainsawCrunchTimer fits in
// the existing padding. VALIDATE_SIZE(CWeapon, 0x18) is a no-op unless
// CHECK_STRUCT_SIZES, so this is the only size check.
#include <cstdint>
struct W { int32_t a, b, c, d; uint32_t t; bool r; int8_t x; };
static_assert(sizeof(W) == 0x18, "CWeapon padding");
int main() { return 0; }
