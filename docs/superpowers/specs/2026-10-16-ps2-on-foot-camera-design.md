# On-foot follow camera: PS2 parity fix (stories/, 3DS only)

## Problem

Reported symptom: "Accuracy: make camera less clunky — camera tends to
point at Toni's face from below." Confirmed in open space, after exiting a
car or a cutscene, and when walking into walls/corners.

Root-caused against the PS2 EUR boot ELF (`SLES_541.35`) via
`ps2-lcs-decompilation` tooling. All VAs below are from that disassembly.
Scope is `stories/`, 3DS build only — III and miami have no equivalent 3DS
on-foot camera and are not touched.

## Root cause

reLCS's default on-foot camera on 3DS is `CCam::Process_FollowPed`
(`stories/src/core/Cam.cpp:997-1340`), VC's "cam on a string" ported
unmodified. It has **no pitch (Alpha) variable at all** — vertical pose is
whatever `0.5 (target Z offset) + ZoomZExtra[zoom] (-0.14/0.16/0.25) +
m_fCamBufferedHeight` works out to, and the C-stick has no vertical effect
on it in this mode. At the default zoom (`CAM_ZOOM_2`) this is roughly
level; at `CAM_ZOOM_1` the camera sits *below* its own target point
(`ZoomOneZExtra = -0.14`), which looks up at Toni's face. The camera also
resets to this same pose after every car exit/cutscene (jump-cut into
`MODE_FOLLOWPED` calls `SetCameraDirectlyBehindForFollowPed_CamOnAString`),
and wall contact only pulls the camera in radially — it never changes
height, so a corner can leave the camera at this same low pose at close
range.

PS2 LCS's actual on-foot default (VA `0x281f50-0x283db4`, found via the
jump table at `0x3bbe10`, confirmed distinct from the free-aim/lock-on
camera at `0x280ee8`) is a **pitch/yaw orbit camera with a permanent
look-down offset and C-stick pitch control**, structurally close to
reLCS's existing `Process_FollowPed_Rotation` (the `FREE_CAM` Display
option) rather than to `Process_FollowPed`. Full derivation in the Research
appendix below.

## Design

### 1. Dispatch (`Cam.cpp:176-199`)

On `_3DS` only, `MODE_FOLLOWPED` always runs the rewritten
`Process_FollowPed_Rotation` (see §2) unless free aim is active:

```cpp
case MODE_FOLLOWPED:
#if defined(PC_PLAYER_CONTROLS) || defined(_3DS)
	if (CCamera::m_bUseMouse3rdPerson)
		Process_FollowPedWithMouse(...);
	else
#endif
#ifdef _3DS
		Process_FollowPed_Rotation(...);   // always, on 3DS, when not free-aiming
#else
#ifdef FREE_CAM
		if (CCamera::bFreeCam)
			Process_FollowPed_Rotation(...);
		else
#endif
		Process_FollowPed(...);
#endif
```

`Process_FollowPed` (the stock VC string cam) is untouched and keeps
running on non-`_3DS` builds exactly as today. `bFreeCam` and the
`FREE_CAM` option stop being read on `_3DS` (see §4).

### 2. `Process_FollowPed_Rotation` body — ported to PS2's algorithm

Rewrite the body of `Cam.cpp:4737-4943` to follow PS2 `0x281f50`, in this
order, using `static` constants scoped to the function in the existing
style:

1. **Pivot.** `TargetCoors = smoothed pedPos + (0,0,0.6)`. (PS2 table
   field 0; was reLCS's `+0.75`.)
2. **Distances.**
   `maxDist = 2.0 + TheCamera.m_fPedZoomValueSmooth` → 2.25 / 3.5 / 4.9 m.
   `minDist = 2.0` (unchanged from reLCS's existing `MinDist`).
   `lookDown = 0.15 + ZoomZExtra[zoom]` → 0.21 / 0.05 / 0.08 rad (12.0° /
   2.9° / 4.6°), using the new `_3DS` `ZoomZExtra` values from §4.
3. **FOV.** Eases toward 70 at `1.0 * dt`; snaps to 70 on reset.
4. **Reset** (`ResetStatics`, or `m_bCamDirectlyBehind`/`InFront`):
   - `Beta` = directly behind the ped (target→source convention, §3), +PI
     if `InFront`.
   - `Alpha = -lookDown` (camera level with the pivot, offset applied via
     `lookDown` in step 9 — **not** the old `Alpha = 0`).
   - `AlphaSpeed = BetaSpeed = 0`, `Distance = 1000` (sentinel, eases down
     next frame per step 10).
   - Seed the previous-source history used by step 5.
5. **String distance.** `d = |TargetCoors − prevSource|`, clamped to
   `[minDist, maxDist]`.
6. **Yaw auto-rotate.** Behind-the-ped auto-rotation scaled by ped speed:
   rate `0.1 * dt * |speed|`, each step capped at `±0.02 * dt`. Skipped
   when the angle to directly-behind is ≥ 170°, or ped speed² ≤ 0.001.
   Includes PS2's blend when the ped walks more than 90° away from the
   camera (weight `0.9^((|Δβ|-90°)·43.77°-scaled)`). **Not ported:** PS2's
   weapon-class fast-rotate mode (`gp-0x34`/`f31=2.5`, gated by unidentified
   functions `0x2af250`/`0x172150`) — flagged as deferred (§ Out of scope).
7. **Pitch.**
   `targetPitch = asin(clamp(prevFront.z, -1, 1)) − lookDown`, clamped to
   `[-85°, +45°]`. `Alpha` eases toward it: `step = (1 - 0.8^dt) *
   (targetPitch - Alpha)`, capped at `±0.1 * dt`.
8. **Stick.** `x`/`y` from `CPad::LookAroundLeftRight`/`UpDown` (raw axis
   on `_3DS` outside free aim, §4). Target speeds:
   `0.007² * |x| * x / 1120 * FOV` (yaw), same with `0.6/1120` (pitch).
   Both smoothed `speed = 0.8^dt * speed + (1-0.8^dt) * target`, clamped
   to `±0.1`, zeroed below `1e-4`. `Beta += BetaSpeed * dt` (wrapped);
   pitch speed is added into `targetPitch` before the Alpha ease in step 7
   runs next frame, so a stick-set pitch persists.
9. **Pose.** Stored `Front = (-cosβ·cosα, -sinβ·cosα, sinα)` (Alpha
   without `lookDown` — this is the field other code reads). `Source` uses
   a *separate* direction with `lookDown` folded in:
   `Source = TargetCoors − (-cosβ·cos(α+lookDown), -sinβ·cos(α+lookDown),
   sin(α+lookDown)) * dist`. Sets
   `m_cvecTargetCoorsForFudgeInter = TargetCoors`.
10. **Collision** — ray only, no sphere loop, same pattern as
    `Process_FollowPedWithMouse`:
    - Bracket with `CWorld::pIgnoreEntity = CamTargetEntity` (landmine
      #11).
    - LOS from `TargetCoors` to `Source`, all entity types.
    - World-geometry hit: `Source = hitPoint + 0.004 * towardTarget`; if
      remaining distance < 0.4125, near clip = `max(d-0.3, 0.05)`.
    - Ped hit with pull-in > 0.2125 m: ignore that ped, re-cast once; same
      near-clip rule, or `min(pullIn-0.35, 0.9)`.
    - No height change, no sphere test. Pitch is never touched by
      collision.
11. **Tail.** `Distance` only shrinks instantly or grows by
    `0.01 * dist * dt` (tracked, not reapplied to `Source` this frame).
    Clear `m_bCamDirectlyBehind`/`InFront`, `ResetStatics = false`,
    `GetVectorsReadyForRW()`.

Pure-math pieces move into file-local helper functions (host-testable, see
Verification): `PS2FollowPedLookDown(zoom)`, `PS2FollowPedStringDist(d,
zoomSmooth)`, `PS2FollowPedPitchStep(target, alpha, dt)`,
`PS2FollowPedStickSpeed(axis, gain, FOV)`, `PS2FollowPedAutoRotateStep(delta,
speed, dt)`.

### 3. Beta convention

The rewritten function uses the Target→Source convention (matching
`Process_FollowPedWithMouse` and PS2), replacing its current
Source→Target convention (AGENTS.md landmine #10). This retires the
landmine for `_3DS` builds: both on-foot orbit cameras now agree. Update
AGENTS.md landmine #10 to say so once the change lands.

### 4. Supporting seams

| File:lines | Change |
|---|---|
| `Camera.cpp:148-158` (`CCamera::Init`) | `#ifdef _3DS`: set `ZoomOneZExtra/Two/Three = 0.06 / -0.1 / -0.07` (PS2 values) instead of VC's `-0.14/0.16/0.25`. Non-`_3DS` unchanged (only read by the now-unused-on-3DS `Process_FollowPed`). |
| `Camera.cpp:412-415` (3DS manual handoff) | `Beta = Wrap(yaw + PI)` unconditionally on `_3DS` for `MODE_FOLLOWPED` handoff (today this is only done for vehicles under `FREE_CAM && bFreeCam`), matching the new convention from §3. |
| `Camera.cpp:1474-1476` (first-person stick gate) | On `_3DS`, do not enter `MODE_1STPERSON` from stick input while on foot — the stick now drives orbit pitch/yaw instead. |
| `Pad.cpp` `LookAroundLeftRight`/`LookAroundUpDown` (`:4062-4122`) | On `_3DS`, outside free aim, return the raw C-stick axis for `MODE_FOLLOWPED` (today these return 0 below \|axis\|≥85 outside `Using3rdPersonMouseCam()`). Free-aim behavior unchanged. |
| `MenuScreensCustom.cpp:61,489,508` | Hide the Display→FreeCam row on `_3DS` (`#ifndef _3DS` around the `FEC_FRC` entry) — that option now controls nothing meaningful since `bFreeCam` is unused on 3DS for `MODE_FOLLOWPED`. |

Left alone in this pass: fight camera, vehicle cameras, free aim/lock-on,
`Process_FollowPed` (non-3DS), look-behind, interior close-in zones (these
shrink `m_fPedZoomValueSmooth`, which automatically shrinks `maxDist` —
no separate change needed), the 3DS comfort/preset layers
(`Camera.cpp:763-997`).

## Expected effect on the symptom

- **Open space:** permanent 3-12° look-down offset at pivot height
  (ped + 0.6m) replaces a pitch-less camera that could sit level with or
  below the pivot. The camera never looks up at Toni's face by
  construction (`lookDown` is always positive).
- **After car exit / cutscene:** reset sets `Alpha = -lookDown` (behind
  and slightly above, looking down), not the old implicit low pose.
- **Walls/corners:** pull-in is purely radial along the ray to Toni —
  pitch is never altered by collision, so a wall cannot drop the camera to
  a low angle.
- Stick gives direct, persistent pitch control, so the player can confirm
  or adjust the angle at any time.

## Research appendix (PS2 derivation, for implementer reference)

- PS2 `CCam::Process` dispatch: jump table VA `0x3bbe10`, index
  `Mode-1`, 46 entries. `MODE_FOLLOWPED` (mode 4) → index 3 → `0x281f50`.
  `0x280ee8` is the separate lock-on/free-aim camera (modes 11/28 only) —
  not the default on-foot camera; this was an earlier wrong assumption,
  corrected during RE.
- `CCamera::Init` PS2 values for `Cams[0]` (VA `0x28d988-0x28da1c`):
  `MinRealGroundDist=1.85`, `CloseInDist=2.0837801-1.85`,
  `ZoomGroundOne/Two/Three = -0.55/1.5/3.5`, **`ZoomOneZExtra/Two/Three =
  0.06/-0.1/-0.07`**, `ZoomZCloseIn=0.9004`.
- Tuning table `0x3938d0` (stride 0x3c), row 0 used (row select global
  `0x3d8650` is 0 in the EUR disc image; row 1 and the alternate wall-push
  branch are not ported — out of scope, see below): `[0.6, 2.0, 0.15, 2.0,
  4.0, 0.8, 0.1, 0.5, 0.8, 0.1, 0.1, 0.02, 1.0, 45°, 85°]`. Field mapping
  used above: `[0]`=pivot Z offset, `[1]`=distance base, `[2]`=look-down
  base, `[3]`=min-dist floor, `[5]`=`0.8` (stick smoothing base),
  `[6]`=`0.1` (pitch ease step cap), `[10]`/`[11]` = auto-rotate rate/cap,
  `[13]`/`[14]` = pitch clamp (45°/85°, used here as +45°/-85°).
- Reset block `0x2825e8-0x28282c`: establishes §2 step 4.
- Yaw auto-rotate `0x282a14-0x282e64`, including the weapon-class special
  mode (`gp-0x34`, functions `0x34f4d0`/`0x2af250`/`0x172150`) that is
  **not** ported (unidentified gating functions — see Out of scope).
- Pitch/stick `0x282e64-0x2831xx`: sticky geometric pitch, clamp
  `[-85°,+45°]` from table fields 13/14, stick gains `0.007²·x/1120` (yaw)
  and `·0.6/1120` (pitch), smoothing base `0.8` from table field 5.
- Collision `0x283320-0x283b00`: LOS-only pull-in, no sphere loop, near
  clip constants `0.4125`/`0.3`/`0.05`/`0.35`/`0.9`, ped-pull-in threshold
  `0.2125`.
- Tail `0x283b00-0x283db4`: `Distance` one-directional ease, final
  `GetVectorsReadyForRW`.

Scratch disassembly used during RE lived under `/tmp/opencode/` (not
committed): `cam_281f50.txt`, `cam_280ee8.txt`, `full.dis`.

## Out of scope / deferred

- PS2's weapon-class fast-rotate auto-rotate mode (§2 step 6) — the gating
  functions (`0x2af250`, `0x172150`) were not identified; porting a guess
  risks inventing behavior. Revisit if a specific weapon's camera feels
  slow to turn on-device.
- PS2 tuning-table row 1 and the `0x3d8650`-gated alternate wall-push
  collision branch — the global is 0 in the EUR disc image, so row 0 is
  believed to be the only reachable path; not confirmed what sets the
  global in other code paths (menus, difficulty, region).
- Any change to the 3DS comfort/preset layers (`Camera.cpp:763-997`). If
  on-device testing shows the stick input feels double-smoothed, a
  follow-up should disable `manual3DS`/`Direct` comfort handling for
  `MODE_FOLLOWPED` specifically — not attempted here to keep this diff
  reviewable.
- Fight camera, vehicle cameras, free aim, lock-on, look-behind,
  `Process_FollowPed` on non-`_3DS` builds, III/miami.

## Files touched

- `stories/src/core/Cam.cpp` — dispatch (§1), `Process_FollowPed_Rotation`
  rewrite (§2), Beta convention (§3).
- `stories/src/core/Camera.cpp` — `CCamera::Init` zoom values, manual
  handoff Beta, first-person stick gate (§4).
- `stories/src/core/Pad.h`/`Pad.cpp` — raw C-stick read for
  `LookAroundLeftRight`/`UpDown` on `_3DS` (§4).
- `stories/src/core/MenuScreensCustom.cpp` — hide FreeCam row on `_3DS`
  (§4).
- `AGENTS.md` — update landmine #10 once this lands.
- `scripts/tests/test_3ds_ps2_follow_ped_cam.py` — new host test (see
  Verification).

## Verification

- `scripts/build.sh relcs` builds clean, no new warnings in the touched
  files.
- `python3 -m unittest discover -s scripts/tests -p 'test_*.py'` and
  `scripts/verify-layout.sh` still pass, including
  `test_3ds_free_aim_latch.py` unchanged.
- New host-compiled test `scripts/tests/test_3ds_ps2_follow_ped_cam.py`,
  following the existing extracted-fragment pattern (e.g.
  `test_3ds_free_aim_point.py`): extract each helper from §2 verbatim from
  `Cam.cpp`, compile with host `c++ -std=c++11
  -fsanitize=address,undefined`, assert:
  - `PS2FollowPedLookDown`: returns `0.21`/`0.05`/`0.08` for zoom 1/2/3;
    all three values are positive (camera always looks down, never up).
  - `PS2FollowPedStringDist`: clamps below 2.0 and above `2.0+zoomSmooth`;
    passes through unchanged in between.
  - `PS2FollowPedPitchStep`: target clamps to `[-85°,+45°]`; large error
    capped at `0.1*dt`; small error moves by `(1-0.8^dt)` fraction.
  - `PS2FollowPedStickSpeed`: quadratic, sign-preserving; pitch axis gives
    0.6× the speed of yaw axis at equal input; zero input gives zero.
  - `PS2FollowPedAutoRotateStep`: zero when angle ≥170° or ped speed² ≤
    0.001; otherwise `0.1*dt*speed*delta` capped at `±0.02*dt`.
- A small source-level check that the `_3DS` dispatch in `CCam::Process`
  sends `MODE_FOLLOWPED` to `Process_FollowPed_Rotation` (not
  `Process_FollowPed`) when free aim is off.
- On-device checklist (`scripts/deploy.sh relcs`):
  1. Open space, flat ground, each zoom level: camera sits above Toni's
     head, looking slightly down, never below his face.
  2. C-stick up/down tilts smoothly and holds; left/right orbits; stick
     input while standing still does not jump to first person.
  3. Walking: camera drifts back behind Toni at a ped-speed-dependent
     rate; walking straight at the camera does not spin it.
  4. After car exit / cutscene: camera starts behind and looking slightly
     down, not low.
  5. Walls/corners: camera pulls in along its line to Toni without
     dropping or looking up, and without clipping into his body.
  6. Free aim enter/exit unaffected, no 180° flip.
  7. Fight camera, vehicle cameras, interior close-in zones still correct.
  8. Display→FreeCam menu row is gone on 3DS.
</content>
