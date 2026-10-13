# Melee lock-on: PS2-faithful fix (stories/)

## Problem

Melee combat in the reLCS 3DS port (fists, brass knuckle, knives/katana/etc.
via the `PED_FIGHT` path, and bat/golf club/nightstick/hammer/chainsaw via
the `PED_ATTACK`/`FireMelee` path) feels clunky compared to the real PS2
game. Two symptoms were singled out for this pass:

- Melee lock-on (holding R to target a ped) feels wrong.
- Toni doesn't turn toward the locked-on target the way he should.

Root-caused against the PS2 EUR boot ELF (`SLES_541.35`) and its weapon
data table (`GAME.DTZ`/`GAME.DAT`), via `ps2-lcs-decompilation` tooling. All
VAs below are from that disassembly. Scope is `stories/` only — III and
miami have no melee lock-on.

## Root causes (PS2 vs reLCS)

1. **Attack input while locked on.** reLCS calls
   `SetAttack(m_pPointGunAt)` every frame the attack button is held
   (`PlayerPed.cpp:1432-1438`), and `SetAttack` for an unarmed/FIGHTMODE
   target routes to `StartFightAttack(GetRandomNumber())` — a random
   button pressure every frame, producing a continuous random-swing loop.
   PS2's equivalent (`ProcessPlayerWeapon`, VA `0x34b100`) only takes this
   per-frame path for non-melee fire types (checked at `0x34b514`); melee
   falls through to the normal `WeaponJustDown` → `StartFightAttack` path,
   i.e. one swing per press.

2. **Which weapons can lock on.** reLCS gates melee lock-on with a hand
   -picked `isMeleeLockOn` test (unarmed, brass knuckle, or
   `WEAPONFLAG_FIGHTMODE`) at `PlayerPed.cpp:1552-1556`. PS2's real
   `CWeaponInfo` table (found in `GAME.DAT` at file offset `0x40a980`,
   stride `0x70`) sets the `CANAIM` bit (`0x40`) on **every** melee weapon,
   including the bat, golf club, nightstick, hammer, and chainsaw. So on
   PS2 all melee weapons can lock on; reLCS's hand-picked set is narrower
   than the original.

3. **Movement while locked on.** reLCS's `MovementDisabledBecauseOfTargeting()`
   (`PlayerPed.cpp:1616-1620`) returns true (freezing the stick) for any
   melee lock-on, because its WEAPON.DAT data lacks `CANAIM_WITHARM`
   (`0x80`). PS2's melee rows all have `CANAIM_WITHARM` set too, so PS2's
   equivalent function (VA `0x34cf48`) returns false and the player keeps
   moving while locked on with a melee weapon.

4. **Lock-on range.** reLCS's melee `m_fRange` values (2.4 unarmed, 2.0
   brass knuckle, 1.8-2.1 for knives, etc., from
   `assets/DATA/WEAPON.DAT`) are far shorter than PS2's: every PS2 melee
   weapon type 0-10 has `m_fRange = 10.0f`, and the chainsaw has `4.0f`.
   `FindWeaponLockOnTarget`/`DoesTargetHaveToBeBroken` both read
   `m_fRange`, so reLCS drops the lock far sooner than PS2 does.

5. **Victim selection while locked on.** reLCS's `ChooseAttackPlayer`
   (`PedFight.cpp:1711-1957`) never reads `m_pPointGunAt`; it always
   re-scans `m_nearPeds` by distance/angle cones, so the ped actually
   struck can differ from the locked-on ped, and the attack's instant
   rotation (`m_fRotationCur = m_fRotationDest`) turns toward whichever ped
   the scan picked, not the lock-on target. PS2's `ChooseAttackPlayer` (VA
   `0x1bf498-0x1bff50`) uses `m_pPointGunAt` as the victim directly when
   it's set, skipping the scan entirely (VA `0x1bf578-0x1bf6f4`).

6. **Cone/distance constants and unarmed move choice are also off** (see
   Design §3) — `maxAttackDist` 2.7 vs PS2's 3.5, a 30°/45° split vs PS2's
   flat 45°, a 1.4-2.7 m walk-up window vs PS2's 2.0-3.5 m, and a random
   punch/kick choice with no victim where PS2 always opens with the right
   hook (and the left hook when there is a victim).

## Design

### 1. Per-frame attack input (`stories/src/peds/PlayerPed.cpp`, `ProcessPlayerWeapon`, ~1430-1471)

Restrict the per-frame `SetAttack(m_pPointGunAt)` call to non-melee weapons:

```
if (weaponInfo->m_eWeaponFire != WEAPON_FIRE_MELEE) {
    if (m_pPointGunAt) SetAttack(m_pPointGunAt);
    ...
} else {
    // existing WeaponJustDown -> StartFightAttack / SetAttack(nil) path
}
```

Melee (locked on or not) always goes through the existing
`WeaponJustDown()` → `StartFightAttack(padUsed->GetWeapon())` /
running-punch `SetAttack(nil)` path. This matches PS2 VA `0x34b514`.

### 2. Lock-on gate, movement, and range (`PlayerPed.cpp` ~1552-1620, `WEAPON.DAT`)

- **Gate.** Replace the `isMeleeLockOn` test with
  `weaponInfo->IsFlagSet(WEAPONFLAG_CANAIM) || GetWeapon()->IsTypeMelee()`.
  This lets every melee weapon lock on, matching PS2's per-weapon `CANAIM`
  bit without touching the WEAPON.DAT flags column (see note below on why
  flipping the flag column is rejected).
- **Sprint.** PS2 only blocks lock-on while sprinting for non-melee
  weapons. Gate the `m_nMoveState != PEDMOVE_SPRINT` term so it only
  applies when `!GetWeapon()->IsTypeMelee()`.
- **Movement freeze.** `MovementDisabledBecauseOfTargeting()` returns
  `m_pPointGunAt && !CANAIM_WITHARM`. Add `&& !IsTypeMelee()` so melee
  lock-on never freezes movement (PS2 result, since all its melee rows
  carry `CANAIM_WITHARM`).
  - Rejected alternative: setting the `CANAIM`/`CANAIM_WITHARM` bits
    (`0xc0`) directly on the melee rows in WEAPON.DAT. In this codebase
    `CANAIM_WITHARM` also drives `CPedIK::AIMS_WITH_ARM` (`Ped.cpp:1220-1223`,
    `PedIK.cpp:180-183`), which makes the ped's arm IK-point at the target
    like a pistol — correct for guns, wrong for a fist or a bat. Keeping
    the flag off and reproducing PS2's three *outcomes* (gate, sprint,
    movement) directly in code avoids that side effect.
- **Range.** Add a `gamefiles/relcs/DATA/WEAPON.DAT` runtime override that
  changes only the melee `m_fRange` column to PS2's values: `10.0` for
  weapon types 0-10 (Unarmed through Katana) and `4.0` for Chainsaw. Every
  other column (damage, radius, anim frames, flags) stays as the existing
  file has it. Register the override in both:
  - `.gitignore` — add `!/gamefiles/relcs/DATA/WEAPON.DAT` next to the
    existing relcs allow-list entries.
  - `scripts/setup-game.sh` — add `DATA/WEAPON.DAT` to the `relcs)` case's
    `copy_runtime_override` list.

  This range also reaches AI code (`PedAI.cpp`) through the shared
  `m_fRange` field — see §4.
- **Body tracking.** `RotatePlayerToTrackTarget()`'s ±25° clamp must be
  skipped for melee outside `PED_FIGHT`, not kept unconditionally. PS2's
  equivalent function skips the clamp whenever the weapon has
  `CANAIM_WITHARM` (true for every PS2 melee row) and the ped isn't
  actively in a fight move; running the clamp every frame for melee (the
  original, PS2-equivalent-not-found choice above) drags the
  stick-derived rotation back toward the target every frame, which reads
  as "movement is frozen" while locked on. Fix: skip the clamp when
  `IsTypeMelee() && m_nPedState != PED_FIGHT`.

### 3. Victim and move selection (`stories/src/peds/PedFight.cpp`, `ChooseAttackPlayer`, ~1711-1957)

- **Locked-on victim takes priority.** When `m_pPointGunAt` is set, use it
  directly as the victim instead of scanning `m_nearPeds`:
  - If the target is on the ground/dying and `CGame::nastyGame` and
    distance < 1.2 m and it fails the "head above position" check, treat
    it as a ground victim.
  - Otherwise, if distance < `weaponAttackDist` (unchanged: `m_fRange` for
    FIGHTMODE weapons, `2.0f` otherwise), treat it as a standing victim.
  - Otherwise, fall through to the no-victim path.
  - Skip the `m_nearPeds` scan entirely in this branch, matching PS2 VA
    `0x1bf578-0x1bf6f4`. The instant rotation (`m_fRotationCur =
    m_fRotationDest`) toward this victim is unchanged — now it reliably
    turns toward the locked-on target.
- **When there's no lock-on target, update the scan's constants to PS2's:**
  - `maxAttackDist`: `3.5f` (was `2.7f`).
  - Standing-victim cone: flat `45°` (was a 30°/45° split by whether the
    ped is mid-step).
  - Ground-victim: unchanged, `1.2 m` / `55°`.
  - Walk-up candidate window: `2.0-3.5 m` / `30°` (was `1.4-2.7 m`, and
    drop the `FIX_BUGS`-gated `< 2.1` narrowing — PS2 has no such
    narrowing).
- **Unarmed move choice** (no change to FIGHTMODE-weapon chaining):
  - Fresh attack with a victim (standing or ground) → `COMBO_A1` (left
    hook).
  - Fresh attack with no victim → `COMBO_A2` (right hook).
  - Remove the random `PUNCH`/`LONGKICK` choice and the `< 1.4 m`
    punch-vs-kick distance split — PS2 has neither.
- **Unarmed combo chaining**, replacing the current A2→A3 / B2→B3-only
  progression. Let `t` = current move's anim time, `fo` =
  `tFightMoves[current].comboFollowOnTime`:

  | Current move | Rule |
  |---|---|
  | `COMBO_A1` / `COMBO_A2` | `t ≤ fo` → advance to the next A move; else if `fo > 0` → switch to the B chain (`current + 3`) |
  | `COMBO_B1` / `COMBO_B2` | `fo > 0 && t ≤ fo` → switch to the A chain (`current - 3`); else advance to the next B move |

  `Fight()`'s existing contact-node mapping (`PED_FOOTR` for
  `LONGKICK`/`ROUNDHOUSE`/`GROUNDKICK`, `PED_HEAD` for the headbutt,
  `PED_HANDR` otherwise) is unchanged. The `PedFightMoves` alias hack
  (`FIGHTMOVE_PUNCH`/`FWDRIGHT`/`LONGKICK`/`ROUNDHOUSE`) is no longer
  needed by `ChooseAttackPlayer`'s unarmed path once this lands; leave the
  aliases in `Ped.h` for now since `Fight()` and `ChooseAttackAI` still use
  them (no behavior change there).

### 4. AI melee approach spacing (`stories/src/peds/PedAI.cpp`, ~6828-7021)

The WEAPON.DAT range change in §2 affects `m_fRange` readers outside the
player lock-on path. Port PS2's approach-and-keep-distance math (VA
`0x31e0b0-0x31e860`) so AI melee peds still close to a sensible distance
instead of hovering 5 m away at the new 10 m range:

- `wepRange = weaponInfo->m_fRange * 0.5f` (unchanged formula, now fed a
  bigger range).
- **Melee weapon types other than Unarmed/BrassKnuckle** (ScrewDriver
  through Chainsaw): seek the victim's position directly and keep
  `max(0.4f * wepRange, 0.8f)` away. Skip `FindMeleeAttackPoint` for these
  types — PS2 doesn't call it here.
- **Victim entering a vehicle** and `wepRange > 2.0f`: seek the victim's
  position, `wepRange = 1.0f`, keep `0.5f` (unchanged from current code,
  confirmed present on PS2 too).
- **Unarmed / BrassKnuckle:** keep the existing attack-point-seeking logic
  for the near case; for the far case (`dist > 5.0f` or no player victim),
  keep `max(0.9f * wepRange, 0.8f)` then `wepRange *= 1.1f` (unchanged
  formula). The exact PS2 behavior for the *near* unarmed case (VA
  `0x31e2d4`) needs full decoding during implementation — carry over
  today's `GetMeleeAttackCoords`/`FindMeleeAttackPoint` call there unless
  the decode shows otherwise, and fix the distance passed in if it does.
- **Remove the `ANIM_STD_FIGHT_SHUFFLE_B` step-back** that reLCS added to
  this function (~line 6949) — it has no PS2 equivalent in this code path.
- **Other `m_fRange` readers to check against PS2 during implementation**
  and port if they diverge: `PedAI.cpp:1357` (`OBJECTIVE_DESTROY_CAR`) and
  `PedAI.cpp:6548` (ranged vehicle-attack decision). `PedFight.cpp`'s own
  `weaponAttackDist`/`0.85*range`/`0.75*range` FIGHTMODE-chain reads are
  already PS2-faithful (PS2's `ChooseAttackPlayer` reads the same field) —
  no change needed there. Confirm `Cam.cpp`'s 3DS free-aim range read
  excludes melee weapons (expected, not yet double-checked).

## Out of scope / deferred

- **Deferred by user request:** removing the `nPlayerInComboMove`
  one-follow-on-per-session limit in `Fight()` (~`PedFight.cpp:1517-1529`),
  which currently caps unarmed combos at 2 hits. PS2's `Fight()` wasn't
  disassembled during this pass, so lifting this limit needs its own RE
  pass before it's done with confidence.
- `PlayHitSound` being fully disabled (`#if 0`) — no fist-impact SFX.
- The per-move `hit_l_hook`/`hit_r_hook`/etc. victim reaction animations
  being loaded but never used (victim reactions are collapsed to
  front/back/left/right).
- `ComboA_3` (uppercut)'s empty strike window (`startFireTime == endFireTime
  == 15 frames`) — the PS2 `FISTFITE.DAT` has the identical values, so this
  is not a porting bug; whether PS2's strike-window test is inclusive in a
  way that makes 15==15 still connect is unconfirmed and out of scope here.

## Files touched

- `stories/src/peds/PlayerPed.cpp` — §1, §2 (gate, sprint, movement).
- `stories/src/peds/PedFight.cpp` — §3 (victim selection, constants, move
  choice, combo chaining).
- `stories/src/peds/PedAI.cpp` — §4 (AI melee approach distance).
- `gamefiles/relcs/DATA/WEAPON.DAT` — new runtime override (§2).
- `.gitignore` — allow-list entry for the above.
- `scripts/setup-game.sh` — `copy_runtime_override` entry for the above.

## Verification

- `scripts/build.sh relcs` builds clean.
- `python3 -m unittest discover -s scripts/tests -p 'test_*.py'` and
  `scripts/verify-layout.sh` still pass.
- Add one host-compiled fragment test for the new unarmed combo-chain rule
  (§3), following the existing pattern in `scripts/tests/` for extracted
  logic fragments.
- On-device manual test matrix: fists, baseball bat, and a knife-class
  weapon, each with the target locked on and not locked on, across all
  four `CPad::Mode` control schemes (`CURMODE` 0-3 — see the
  `gta-3ds-input-mapping` skill and `AGENTS.md` landmine #9). For each
  combination, check:
  - Toni can still move while locked on with a melee weapon.
  - The ped actually struck matches the locked-on target.
  - Holding the attack button swings once per press, not continuously.
  - The lock breaks only around the new (longer) range, not early.
  - AI melee peds (fists and a melee weapon) close to a reasonable
    distance before attacking, with no new backward step.
