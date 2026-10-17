# Melee camera: no fight cam on 3DS (PS2 parity)

## Bug

During melee the camera yaw swings from one side of the player to the other.
It happens on every punch, with or without lock-on, and even while kicking a
ped that is already on the ground (the player's heading barely changes, so the
swing comes from the camera itself).

## Root cause

`CCamera::CamControl` (`stories/src/core/Camera.cpp`, "Check if entering fight
cam" block) requests `CCam::MODE_FIGHT_CAM` whenever the player is in
`PED_FIGHT`, or holds a baseball bat in `PED_ATTACK`:

```cpp
// Check if entering fight cam
if(!m_bFirstPersonBeingUsed){
	if(FindPlayerPed()->GetPedState() == PED_FIGHT && !m_bUseMouse3rdPerson)
		ReqMode = CCam::MODE_FIGHT_CAM;
	if(((CPed*)pTargetEntity)->GetWeapon()->m_eWeaponType == WEAPONTYPE_BASEBALLBAT &&
	   FindPlayerPed()->GetPedState() == PED_ATTACK && !m_bUseMouse3rdPerson)
		ReqMode = CCam::MODE_FIGHT_CAM;
}
```

So melee leaves the PS2-ported on-foot follow cam
(`CCam::Process_FollowPed_Rotation`, see
`2026-10-16-ps2-on-foot-camera-design.md` and
`2026-10-17-ps2-follow-cam-parity-fixes-design.md`) and runs
`CCam::Process_Fight_Cam` (`stories/src/core/Cam.cpp`), inherited unchanged
from re3. That function has a decompilation bug: it stores the *relative*
angle `DeltaBetaLeft`/`DeltaBetaRight` into `m_fTargetBeta`, which
`WellBufferMe` then treats as an *absolute* yaw. Every `WeaponJustDown()`
(every punch or kick) re-picks that bogus target, so the camera swings each
strike.

## PS2 reference (`SLES_541.35`)

- `CCam::Process` dispatch table `0x3bbe10` (index `Mode-1`): entry 36
  (`MODE_FIGHT_CAM`) → `0x27c428`, a line-for-line match of
  `Process_Fight_Cam` (same 3.0/1.0/125° constants and `WellBufferMe`
  constants). PS2 stores the absolute `BetaLeft`/`BetaRight` there
  (`swc1 $f20/$f21, 0xc0($s0)` at `0x27c5b4-0x27c5bc` and
  `0x27c5f0-0x27c608`) — confirming the reLCS delta bug.
- **But PS2 never enters that mode.** In PS2 `CCamera::CamControl` (contains
  `0x28af3c`), `ReqMode` (`0x2ada($gp)` = `0x3d9bca`) is assigned only
  constants other than 36/43, or values from: `TheCamera+0xa44` (written only
  by `SetNewPlayerWeaponMode` `0x2931b0`, whose five callers pass
  7/8/0x22/0x2d/0x2e/0xb), `+0x1cc8` (4 or 0x12), `+0xa38` (no writers),
  `0x3d9bd4` (0x20), `0x3d6efc` (debug override, only ever 0). No halfword
  store of 0x24 exists anywhere in the binary, and CamControl has no
  `PED_FIGHT` check feeding `ReqMode`. `MODE_FIGHT_CAM` is dead code on PS2.
- PS2's follow cam (`0x281f50-0x283db4`) has no ped-state reads; its only
  fight awareness is `ForceCameraBehindPlayer` (`0x172150`), already ported in
  `stories/src/core/Pad.cpp` (no force-behind during `PED_ATTACK`/`PED_FIGHT`
  while looking behind).

So on PS2, melee simply stays in the normal on-foot follow cam.

## Fix

Wrap the "Check if entering fight cam" block in `CCamera::CamControl`
(`stories/src/core/Camera.cpp`) in `#ifndef _3DS` … `#endif`, with a one-line
comment citing PS2 (CamControl never requests `MODE_FIGHT_CAM`). On `_3DS`,
melee stays in `Process_FollowPed_Rotation`, exactly as on PS2. Non-`_3DS`
builds keep the original behavior.

## Goals

- No per-strike camera swing during melee (fists, bat, other melee weapons,
  ground kicks), with or without lock-on.
- Melee camera behavior matches PS2: the ordinary on-foot follow cam.

## Non-goals

- Fixing `Process_Fight_Cam`'s delta bug. It becomes unreachable on `_3DS`;
  leave it as inherited (my call — smallest change, avoids touching dead code).
- `III/` and `miami/`. They have the same block and the same delta bug, but
  they are III/VC ports, and the PS2 LCS evidence does not apply to them.
- Fight-cam ↔ follow-cam transition blending (`Camera.cpp` mode-transition
  code). It no longer triggers on `_3DS`.
- Tuning the follow cam's response to per-strike heading snaps in
  `CPed::Fight` — that gentle auto-rotate is PS2 behavior.

## Anti-goals

- Changing non-`_3DS` behavior.
- Touching the free-aim / lock-on camera (`Process_FollowPedWithMouse`,
  reached via `m_bUseMouse3rdPerson`); the gated block already excludes it.

## Validation

- A small regression test in `scripts/tests/` (same style as
  `test_ai_melee_attack_gate.py`): read `Camera.cpp`, find the
  `ReqMode = CCam::MODE_FIGHT_CAM;` assignments in `CamControl`, and assert
  each sits inside an `#ifndef _3DS` region.
- Full test suite: `python3 -m unittest discover -s scripts/tests -p 'test_*.py'`.
- Build: `scripts/build.sh relcs` (with the vendored devkitARM exports).
- On-device (user): punch, kick a downed ped, swing the bat, with and without
  lock-on — the camera should stay behind the player without swinging.

## Commit

`stories:` scope, stating the change affects `stories/` only.
