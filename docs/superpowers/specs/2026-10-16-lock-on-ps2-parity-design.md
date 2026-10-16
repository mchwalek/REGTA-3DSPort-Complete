# Auto-aim lock-on: PS2 parity fix (stories/)

## Problem

Reported symptom (from `TODO.txt`): "Accuracy: autoaim too sensitive (snaps
to far peds)." Specifically: lock-on (holding R/L1 to target a ped) locks
onto peds that are off-screen, and in general locks onto peds farther away
than feels right, when a closer or more visible ped is available.

Root-caused against the PS2 EUR boot ELF (`SLES_541.35`) via
`ps2-lcs-decompilation` tooling. All VAs below are from that disassembly.
Scope is `stories/` only — III and miami have no lock-on target scoring
identical to reLCS's current code, and are not touched by this fix.

## Root causes (PS2 vs reLCS)

reLCS's `CPlayerPed::EvaluateTarget`/`FindWeaponLockOnTarget`
(`stories/src/peds/PlayerPed.cpp:1136-1287`) score every candidate ped by
`closeness = -dist2D - 5.0 * |angle_from_forward|`, with `+30` for a
priority target (hostile/mission-objective ped), and keep the highest
score. Weapon ranges (`m_fRange`, from WEAPON.DAT) already match PS2's
values — range is not the cause. Disassembling PS2's equivalent functions
found reLCS's scoring and gating logic is missing six pieces of PS2
behavior, none of which shorten the *range*, but several of which change
*which* ped wins:

1. **No on-screen bonus.** PS2's `EvaluateTarget` (VA `0x34d510`) adds
   `+15.0` to the score if the candidate is on-screen (`GetIsOnScreen()`-
   equivalent, VA `0x306008`, a frustum/bounding-sphere test). reLCS has no
   such term, so an off-screen candidate can outscore an on-screen one at
   a similar distance/angle — this is the direct cause of "locks onto
   something off-screen."
2. **No mission-character bonus.** PS2 adds `+40.0` if the candidate is a
   ped with `CharCreatedBy == MISSION_CHAR` (`0x1ac` on PS2's `CPed`, =
   reLCS's `CPed::CharCreatedBy`, `Ped.h:613`). reLCS has no such term.
3. **Looser line-of-sight in the initial search.** PS2's
   `FindWeaponLockOnTarget` calls `OurPedCanSeeThisOne(ped, true)`
   (shootable objects block LOS); reLCS's initial search passes `false`
   (shootables-block is only `true` in the L/R cycle variant,
   `:1216`). So reLCS can lock through objects PS2 would have blocked.
4. **No cooldown after losing a target.** PS2 sets a 6-frame cooldown
   (`0xc88`) whenever the lock-on gate fails while a target exists
   (including releasing Target), during which no new lock is attempted.
   reLCS has no cooldown, so releasing and immediately re-pressing Target
   re-locks instantly, which can feel like "snaps to [a different, often
   farther] ped" the instant Target is tapped again.
5. **No re-lock-on-cooldown-expiry.** PS2 re-triggers the initial lock
   search when the cooldown reaches 0 *and* Target is still held
   (`0x34b13c`), giving a deliberate ~0.2s delay-then-lock instead of an
   instant lock on press.
6. **No L1-held suppression of the initial lock.** PS2 suppresses the
   initial lock trigger while L1 is held in control modes 0-2 (L1 is the
   free-look/cycle modifier in those modes; mode 3 uses L1 as Target
   itself, so the suppression doesn't apply there). reLCS has no such
   guard.
7. **(Found while re-verifying the cycle logic for this spec) No angular
   window on L/R cycling.** PS2's `EvaluateNeighbouringTarget` (VA
   `0x34d740`) rejects candidates more than 50° (`0.8727` rad) off the
   camera-relative reference angle. reLCS has no such window, so L/R
   cycling can jump to a ped almost behind the camera.
8. **No nil-target cycling.** On PS2, if the lock-on target was lost
   because it died or entered a vehicle, L/R can still cycle to the next
   candidate using the dead target's last known position as the reference.
   reLCS's `FindNextWeaponLockOnTarget` requires an existing
   `m_pPointGunAt` and isn't reachable with no target at all.

Items 1-3 are the direct fix for the reported symptom. Items 4-8 are full
PS2 parity for the rest of the lock-on trigger/cycling behavior, scoped in
at the user's request.

## Design

### 1. New `CPlayerPed` fields (`stories/src/peds/PlayerPed.h`)

Add, near the existing lock-on-related fields (`PlayerPed.h:20-52`):

```cpp
uint8 m_nLockOnCooldown;     // frames remaining before a new lock-on may be attempted (PS2 0xc88)
bool m_bLostLockOnTarget;    // true if a target was lost to death/vehicle-entry, for cycle-with-no-target (PS2 0xc94)
CVector m_vecLastLockOnPos;  // position of the lost target, used as the cycle reference (PS2 0xca0)
```

All three are runtime-only (no save format change). Zero-initialize in the
`CPlayerPed` constructor near `PlayerPed.cpp:196`.

### 2. Scoring (`EvaluateTarget`, `PlayerPed.cpp:1136-1157`)

Factor the closeness formula into a pure static helper (also makes it
host-testable):

```cpp
static float
LockOnCloseness(float dist, float angle, bool priority, bool onScreen, bool missionChar)
{
	float closeness = -dist - 5.0f * Abs(angle);
	if (priority) closeness += 30.0f;
	if (onScreen) closeness += 15.0f;     // PS2 0x34d510 -> GetIsOnScreen() 0x306008
	if (missionChar) closeness += 40.0f;  // PS2: CharCreatedBy == MISSION_CHAR
	return closeness;
}
```

`EvaluateTarget` computes `dist`/`angleBetweenUs` as today, then calls:

```cpp
float closeness = LockOnCloseness(dist, angleBetweenUs, priority,
	candidate->GetIsOnScreen(),
	candidate->IsPed() && ((CPed*)candidate)->CharCreatedBy == MISSION_CHAR);
```

`CEntity::GetIsOnScreen()` already exists (`Entity.cpp:533-536`,
`TheCamera.IsSphereVisible(GetBoundCentre(), GetBoundRadius())`) — no new
helper needed there. `EvaluateNeighbouringTarget` (cycling) is unaffected by
this change; its own scoring is purely angular and untouched here (see §4
for its separate fix).

### 3. Line-of-sight in the initial search (`FindWeaponLockOnTarget`, `:1259`)

```cpp
OurPedCanSeeThisOne(pedToCheck)   ->   OurPedCanSeeThisOne(pedToCheck, true)
```

Matches PS2; the L/R cycle variant (`FindNextWeaponLockOnTarget`) already
passes `true` and is unchanged.

### 4. Gate, cooldown, and nil-target cycling (`ProcessPlayerWeapon`, `PlayerPed.cpp:1562-1622`)

**Per-frame, before the existing gate condition:**

```cpp
bool targetJustDown = padUsed->TargetJustDown();
if (m_nLockOnCooldown) {
	m_nLockOnCooldown--;
	if (m_nLockOnCooldown == 0 && padUsed->GetTarget())
		targetJustDown = true;   // PS2 0x34b13c: re-lock when cooldown expires with Target held
}
if (!padUsed->GetTarget())
	m_bLostLockOnTarget = false;  // PS2 0x34b198
```

**Gate structure** (the existing gate boolean expression at `:1563-1564` is
unchanged; only the body changes):

```cpp
if (gate) {
	if (m_nLockOnCooldown == 0) {
		if (m_pPointGunAt) {
			// ...existing with-target branch (break checks, RotatePlayerToTrackTarget,
			// L/R cycle, SetNewPlayerWeaponMode, UpdateAimingCoors)...
			// Where the target is dropped because it died or entered a vehicle, add
			// before the existing ClearWeaponTarget() call:
			//   m_vecLastLockOnPos = m_pPointGunAt->GetPosition();
			//   m_bLostLockOnTarget = true;
		} else if (!CCamera::m_bUseMouse3rdPerson) {
			if (m_bLostLockOnTarget) {
				if (padUsed->ShiftTargetLeftJustDown())  FindNextWeaponLockOnTarget(nil, true);
				if (padUsed->ShiftTargetRightJustDown()) FindNextWeaponLockOnTarget(nil, false);
			}
			if ((targetJustDown && (CURMODE == 3 || !padUsed->GetLeftShoulder1()))
			    || TheCamera.m_bJustJumpedOutOf1stPersonBecauseOfTarget)
				FindWeaponLockOnTarget();
		}
	}
} else if (m_pPointGunAt) {
	ClearWeaponTarget();
	m_nLockOnCooldown = 6;   // PS2 0x34bd70
}
```

The existing `m_pPointGunAt` dead/vehicle drop path (inside the with-target
branch) is extended to record `m_vecLastLockOnPos`/`m_bLostLockOnTarget` as
shown above, matching PS2 `0x34bbec`.

**3DS interactions (no code change needed, called out for the implementer):**
- The 3DS free-aim target drop (`:1568-1572`, `Is3DSFreeAimActive()`) is
  inside the with-target branch, so it goes through the same
  `ClearWeaponTarget()` path and starts the cooldown — matching PS2, where
  the cooldown is set in the single shared "gate failed with a target"
  path, not a special case.
- The no-target branch stays behind `!m_bUseMouse3rdPerson` (already true
  today), so a cooldown-expiry re-lock cannot fire while free-aiming.
- The L1 guard uses `CURMODE` (reLCS's control-mode enum), matching PS2
  mode 4 (`CURMODE == 3` in reLCS numbering is Target-on-L1); see
  `gta-3ds-input-mapping` skill and `AGENTS.md` landmine #9 — this is
  exactly the kind of multi-button check that landmine warns about, and is
  written mode-aware from the start.

### 5. Nil-target cycle reference (`FindNextWeaponLockOnTarget`, `PlayerPed.cpp:1196-1236`)

Add a nil guard for `previousTarget` at the top:

```cpp
CVector refPos = previousTarget ? previousTarget->GetPosition() : m_vecLastLockOnPos;
```

Use `refPos` wherever the function currently computes
`previousTarget->GetPosition()` for the camera-relative `referenceBeta`.
The existing `pedToCheck != previousTarget` skip is a no-op when
`previousTarget` is nil, which is correct (no ped to exclude).

### 6. Angular window on cycling (`EvaluateNeighbouringTarget`, `PlayerPed.cpp:1110-1134`)

Add PS2's 50° window, rejecting out-of-cone candidates outright:

```cpp
if (Abs(angleBetweenUs) >= 0.8727f)  // PS2 0x34d740, 50 degrees
	return;
```

Placed after `angleBetweenUs` is computed and `LimitAngle`'d, before the
`lookToLeft` branch that currently produces the `-100000.0f` sentinel for
wrong-side candidates — out-of-window candidates now get the same rejection
treatment as wrong-side ones.

## Expected effect on the symptom

An on-screen ped 15 m away now beats an off-screen ped 25+ m away (15-point
on-screen bonus roughly offsets ~3 m of distance difference per the `-dist`
term, so the gap has to be fairly large before off-screen wins — matches
PS2). A ped fully hidden behind a prop or crate no longer qualifies for the
initial lock at all. Re-pressing Target within 6 frames of losing a lock no
longer instantly re-locks onto a different (possibly farther) ped.

## Out of scope / deferred

- The unresolved PS2 global at `0x3d8654` (read in `FindNextWeaponLockOnTarget`'s
  nil-target reference-position check) was not identified; its effect
  appears to only matter when `previousTarget` is non-nil, where reLCS
  already has a valid `previousTarget` to use directly, so it has no
  bearing on this design.
- No change to III/miami — their `PlayerPed.cpp` lock-on code is not
  identical to reLCS's current implementation and was not RE'd against PS2
  Vice City/III for this pass.
- No change to weapon ranges, `DoesTargetHaveToBeBroken`, `CanIKReachThisTarget`,
  `IsThisPedAnAimingPriority`, or the 40m `OurPedCanSeeThisOne` cap — all
  confirmed identical to PS2 already.

## Files touched

- `stories/src/peds/PlayerPed.h` — §1, new fields.
- `stories/src/peds/PlayerPed.cpp` — §2-§6 (scoring, LOS, gate/cooldown,
  nil-target cycling, angular window).
- `scripts/tests/test_lock_on_closeness.py` — new host test (see
  Verification).

## Verification

- `scripts/build.sh relcs` builds clean.
- `python3 -m unittest discover -s scripts/tests -p 'test_*.py'` and
  `scripts/verify-layout.sh` still pass.
- New host-compiled test `scripts/tests/test_lock_on_closeness.py`,
  following the existing extracted-fragment pattern (e.g.
  `test_unarmed_combo_chain.py`): extract `LockOnCloseness` verbatim from
  `PlayerPed.cpp`, compile with host `c++ -std=c++11
  -fsanitize=address,undefined`, assert:
  - Base formula: 10 m at 0 rad gives `-10.0`.
  - Each bonus applied alone: `+30`, `+15`, `+40`.
  - Symptom case: a 12 m on-screen ped outscores a 25 m off-screen ped.
  - A mission-char ped outscores a closer ordinary ped by enough to flip
    the ranking in a case where it wouldn't without the bonus.
- The cooldown, L1 suppression, and cycling logic depend on live `CPad` and
  ped-pool state and are not practical to unit-test on the host; verify
  on-device:
  - Lock-on prefers an on-screen ped over a farther off-screen one.
  - Lock-on ignores a ped fully hidden behind a prop.
  - Releasing and immediately re-pressing Target does not instantly
    re-lock; holding Target through the loss re-locks automatically after
    the cooldown.
  - L/R cycling after a kill picks a target near the dead ped's last
    position, and does not jump to a ped outside a roughly 50° cone.
  - Repeat the above across all four `CPad::Mode` control schemes
    (`CURMODE` 0-3), per `AGENTS.md` landmine #9.
