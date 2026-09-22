# PS2-faithful third-person free aim (`stories/`, 3DS)

## Problem

On PS2, LCS's manual-aim mode ("Free Aim") keeps the camera in third
person: Toni raises his arm and aims, the reticle is a small ring+dot near
screen center, and the player adjusts aim with the right analog control
(mapped by the port to the left stick — see below). GXT evidence:
`MAIN/FEC_FRA` = "Free Aim", tutorial `VIC4/HELP42` = "While targeting, tap
~FREE1~ to enter Free Aim mode, then use the ~FREE2~ to adjust your aim."
This is the only free-aim string in the whole PS2 GXT (5759 entries
searched). `FEC_FRA` is bound to L3 on PS2 (derived by aligning the ELF's
on-foot control-label tables against reLCS's own
`DrawControllerSetupScreen` ordering — LCS has no crouch, so the L3 slot VC
uses for crouch was free for Free Aim).

On 3DS, commit `df4e8f9` ("correct face-button mapping and generalize
free-aim to all aimable weapons") widened the previously rifle-only
first-person aim hack (`MODE_M16_1STPERSON`) to every `WEAPONFLAG_CANAIM`
weapon — which, per `WEAPON.DAT`, is every firearm including the pistol.
Result: the camera snaps to the head bone (first person, no Toni visible),
and firing routes through `CWeapon::FireM16_1stPerson`
(`weapons/Weapon.cpp:2462-2493`), which does
`Cams[ActiveCam].Beta/Alpha += ((rand()&127)-64) * mult` on every shot — an
unbounded random walk (up to ±0.73°/shot for a pistol, never re-centered).
That is the reported "reticle slightly moves after each shot" — stock reLCS
code that PS2 never ran for a non-rifle weapon, now reachable because
`CWeapon::Fire` dispatches on camera mode, not weapon type.

## Root cause

`-D_3DS` → `GTA_HANDHELD` (`core/config.h:172-174`) → `PC_PLAYER_CONTROLS`
undefined (`config.h:189-191`) → `CCamera::m_bUseMouse3rdPerson`
permanently `false` on 3DS. This silently kills reLCS's own **existing**
PC third-person free-aim implementation (over-the-shoulder camera, arm-raise
animation, camera-relative fire direction, and a correct PS2-style ring+dot
reticle) — all of it is present in the source tree and dead only because of
this one flag. Separately, `PlayerPed.cpp:1408-1455`'s 3DS-only
`enterFreeAim` branch (added by `df4e8f9`) routes every aimable weapon into
the abandoned rifle-only first-person mode instead.

## Decision

Do not build a new third-person aim system. Reactivate reLCS's existing PC
implementation (which is PS2-faithful in mechanism: arm raise, third-person
camera, stick-adjustable aim, camera-relative shots) by latching
`CCamera::m_bUseMouse3rdPerson` and `CCamera::bFreeCam` to `true` for the
duration of a free-aim input, and delete the first-person routing entirely.

### Controls
- Hold **R**: lock-on if a target exists (unchanged).
- **ZL / ZR** while holding R: cycle lock-on target left/right (moved off L,
  which collided with the free-aim chord).
- **Tap L** while holding R: enter free aim (matches PS2's "tap FREE1 while
  targeting"). Third-person camera stays; Toni raises his arm; **left
  stick** adjusts aim (not C-stick — PS2's adjust-aim token `FREE2` is
  already mapped to `"CIRCLE PAD"` in `Messages.cpp:671`).
- **Release R**: exit free aim. (PS2's GXT has no exit instruction; this is
  the chosen 3DS-port convention — free aim is a sub-mode of targeting.)
- Movement while free aiming: unchanged stock behavior
  (`WEAPONFLAG_CANAIM_WITHARM` already permits walking with pistol-class
  weapons and roots the player for rifles/shotguns).
- Sniper rifle / rocket launcher / camera keep their own dedicated scopes,
  untouched.

### Mechanism
A latch drives the two raw statics directly (not a new predicate), because
existing readers are split between `CCam::Using3rdPersonMouseCam()`
(`m_bUseMouse3rdPerson && Mode==MODE_FOLLOWPED`) and the raw
`CCamera::m_bUseMouse3rdPerson`/`CCamera::bFreeCam`:

```
enter: saved = bFreeCam; m_bUseMouse3rdPerson = true; bFreeCam = true;
exit:  m_bUseMouse3rdPerson = false; bFreeCam = saved;
```

`bFreeCam = true` is mandatory, not incidental —
`PlayerPed.cpp:1979-1984` and `Ped.cpp:9512-9514` route to
`PlayerControl1stPersonRunAround` (the PC strafe controller) instead of
`PlayerControlFighting` when `Using3rdPersonMouseCam() && !bFreeCam`.

Exit triggers: `!GetTarget()` (R released), `ArePlayerControlsDisabled()`
(e.g. paused mid-aim — prevents the options menu incorrectly showing "Free
Cam: On"), entering a vehicle, or player ped gone.

This flips on, with zero further call-site edits, code that is already
present and known-good on PC:
- `Cam.cpp:185-189` → `Process_FollowPedWithMouse` (over-the-shoulder aim
  camera, reads the stick via `LookAroundLeftRight/UpDown`)
- `PlayerPed.cpp:1507-1553` → arm raise, `SetAimFlag`, `m_bFreeAimActive`
- `PedFight.cpp:337-350` → aim animation
- `Weapon.cpp:961-994` → shots follow the reticle (camera-relative)
- `Hud.cpp:357-375` → `CHud::DrawSolidStandardSight`, the existing
  3DS-added ring+dot reticle that visually matches the PS2 screenshot —
  currently unreachable because its guard requires
  `Using3rdPersonMouseCam()`

### Deleted
- `PlayerPed.cpp:1411-1430`'s `enterFreeAim`/`MODE_M16_1STPERSON` routing
  block.
- `g3DSSuppressRifleFireUntilRelease` and its readers
  (`PlayerPed.cpp:939-940, 958-972`).
- The old `Get3DSFreeAim()` raw-chord implementation
  (`core/Pad.cpp:2209-2214`), replaced by an edge-triggered latch.

`FireM16_1stPerson`'s per-shot drift becomes unreachable by construction —
no weapon can reach `MODE_M16_1STPERSON` from the free-aim path anymore.

## Explicitly out of scope (considered, rejected)

- **Reticle screen position** (`Camera.cpp:247-248`,
  `m_f3rdPersonCHairMultX/Y = 0.53f/0.4f`): unchanged. These are tuned
  against `Process_FollowPedWithMouse`'s camera offsets; a screenshot
  eyeball estimate of "≈0.50/0.50" isn't a reliable basis to retune them in
  isolation. Revisit on hardware if the reticle looks wrong.
- **Rifle vs. pistol reticle sprite difference** (`Hud.cpp:363`: M4/Ruger/M60
  draw `HUD_SITEM16`, everything else draws the ring): unchanged. The PS2
  ELF ships a dedicated `siteM16` sprite string, so a distinct rifle sight
  is PS2-faithful, not a port artifact.

## Other changes
- Docs (`README.md:623`, `stories/README.md:158`, currently "L + R |
  First-person rifle aim") updated to describe tap-L-while-holding-R free
  aim and the ZL/ZR cycle-target change.
- `text/Messages.cpp:670`: `FREE1` token `"L + R"` → `"L"` (GXT sentence
  already says "while targeting", implying R is held).

## Verification

No 3DS console available for this change. Verification is limited to:

```sh
python3 -m unittest discover -s scripts/tests -p 'test_*.py'
scripts/verify-layout.sh
scripts/build.sh relcs
```

The build is the real check for the `PlayerPed.cpp` deletion (a dangling
`g3DSSuppressRifleFireUntilRelease` reference fails to compile). One new
test, `scripts/tests/test_3ds_free_aim_latch.py`, extracts the latch state
machine and compiles it with the host `c++` to assert enter/exit
transitions across all four exit conditions — the rest of the change is
deletion and flag assignment, not independently unit-testable.

## Accepted residual risks (no hardware to verify)

- `Ped.cpp:1466` starts computing `m_fWalkAngle` once
  `m_bUseMouse3rdPerson` is set — may affect walk/aim animation blending.
- `LookAroundLeftRight/UpDown`'s `>85` fast branch (3.97× gain,
  `Pad.cpp:3884-3917`) still wins at full stick tilt over the gentler
  `Using3rdPersonMouseCam()` fine-aim curve (1.98×) — may need an
  on-device tuning pass.
