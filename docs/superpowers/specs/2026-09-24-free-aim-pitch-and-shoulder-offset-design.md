# Free-aim pitch envelope and shoulder offset (`stories/`, 3DS)

## Problem

Two accuracy defects in the 3DS third-person free-aim camera
(`docs/superpowers/specs/2026-09-22-ps2-faithful-free-aim-design.md`),
found by comparing on-device screenshots against the PS2 original:

1. **Pitch too restricted downward.** `ps2_down_pitch.png` shows PS2's
   max-down free aim at roughly −60°: the camera looks down at a taxi roof
   from above, garage doors seen from the top. `3ds_down_pitch.bmp` caps at
   −20°: garage doors are still seen from the side. 3DS free aim cannot look
   anywhere near as far down as PS2 can.
2. **Reticle sits on the player's head.** In `ps2_down_pitch.png` the
   reticle (screen center) is offset right of and slightly above Toni's
   head, roughly 0.5 m in world space at the camera's ~2.5 m distance. On
   3DS (`3ds_down_pitch.bmp`) the reticle lands exactly on Toni's head,
   because the camera orbits a point with no lateral offset.

## Root cause (from `SLES_541.35` disassembly)

reLCS's 3DS free-aim camera (`Cam.cpp:1364-1657`,
`Process_FollowPedWithMouse`, `#ifdef _3DS` blocks added by the prior
free-aim work) integrates the stick directly into camera `Alpha`/`Beta` and
clamps `Alpha` to `[-20°, +40°]` (commit `5678ebb`, citing PS2 VA
`0x34a680`). Disassembly of the real PS2 camera function (VA
`0x280ee8-0x281f4c`) and the ped free-aim function it calls (VA `0x34a680`)
shows this is not how PS2 works:

- PS2 free aim does not drive the camera angles directly. The stick moves a
  **world-space aim point** (`player+0xcc0`, a dummy entity attached via
  `SetPointGunAt`), clamped by an angle-from-vertical envelope
  `acos(dir.z) ∈ [50°,110°]` (VA `0x34a680`) measured **from the ped's hip
  position**, with accept/reject hysteresis at the boundary, and a
  ±110°-from-forward yaw cone with the same hysteresis. A line-of-sight
  probe (`CWorld::ProcessLineOfSight`) snaps the point to the first surface
  hit along the aim ray.
- The **camera** (VA `0x280ee8`) then takes the lock-on branch (because
  `m_pPointGunAt != nil`): its `Alpha`/`Beta` are derived every frame as
  `atan2` from a pivot point `T` to the aim point, eased in at a flat
  `0.1*dt` rad/step, and — critically — **the camera's own `Alpha` clamp is
  explicitly skipped whenever the free-aim flag is set** (VA
  `0x281928-0x281988`: `if(player->0xcbc == 0) clamp; else no clamp`).
- The `[50°,110°]` envelope bounds the aim **point relative to the ped's
  hip**, not the camera pitch relative to its pivot `T`. `T` sits 0.6 m
  above and 0.55 m right of the ped (see next bullet), so when the aim
  point is LOS-snapped close to a wall or floor, the camera-to-point pitch
  from `T` can be far steeper than the point's hip-relative angle — this is
  exactly the −60° in the screenshot. reLCS's `[-20°,+40°]` clamp applied
  the hip-relative envelope directly to the camera pitch, which is a
  different quantity and is far more restrictive downward.
- The pivot point `T` ("TargetCoors") is built by PS2 fn VA `0x27be28`:
  `T = pedPos + (0,0,0.6) + ped.GetRight()*0.55`, LOS-probed from
  `pedPos+(0,0,0.6)` (on hit, `T = hitPoint + hitNormal*0.1`). reLCS's
  `Cam.cpp:1386-1387` only does `TargetCoors.z += fTranslateCamUp` (0.8, not
  0.6) — no lateral term at all — which is why the reticle sits on the
  head: the orbit center coincides with the head instead of being offset to
  the side.

## Decision

Port PS2's mechanism, not just its constants: drive a free-aim **world aim
point** from the stick with PS2's exact envelope/hysteresis/LOS-snap logic,
build the camera pivot `T` with PS2's lateral shoulder offset, and derive
camera `Alpha`/`Beta` each frame from `T → aim point` with no separate pitch
clamp. This is confined to `stories/src/core/Cam.cpp`; no other file
changes.

### State (file statics in `Cam.cpp`, replacing `s3DSFreeAimTurningIn` /
`s3DSFreeAimGoalBeta`)

```cpp
static CVector s3DSFreeAimPoint;       // world-space aim point (PS2 player+0xcc0)
static float   s3DSFreeAimPrevYawRel;  // previous frame's yaw-vs-forward angle, for yaw hysteresis
```

A plain `CVector`, not a `CEntity` — nothing downstream needs an entity.
IK pitch (`Find3rdPersonQuickAimPitch()` = `-Alpha` on 3DS), IK yaw
(`TheCamera.Orientation`), the fire vector (`CHairMult` 0.5/0.5 = camera
ray), and the reticle sprite (`Hud.cpp` at `CHairMult`) all already derive
from the camera, which now derives from the aim point — no new consumer
needed.

### Per-frame algorithm, inside `Process_FollowPedWithMouse`'s
`if(Is3DSFreeAimActive())` block

Replaces: the quadratic-stick integration (`Cam.cpp:1464-1479`), the
turn-in step and statics (`1360-1361`, `1506-1516`), the yaw cone
(`1517-1527`), and the `_3DS` pitch-clamp branch (`1529-1539`). The
`TargetCoors` computation (`1386-1387`) gains a 3DS free-aim-only branch.

1. **Pivot `T`:** `T = pedPos + (0,0,0.6f) + ped->GetRight()*0.55f`; probe
   `CWorld::ProcessLineOfSight(pedPos+(0,0,0.6f), T, colPt, ...)`; on hit
   `T = colPt.point + colPt.normal*0.1f`. (Non-3DS path keeps
   `TargetCoors.z += fTranslateCamUp` unchanged.)
2. **Entry frame:** `s3DSFreeAimPoint = pedPos + ped->GetForward()*range`
   (`range = CWeaponInfo::GetWeaponInfo(ped->GetWeapon()->m_eWeaponType)->m_fRange`),
   `s3DSFreeAimPrevYawRel = 0`. Camera `Alpha`/`Beta` keep the existing
   entry re-derivation from live geometry (commit `3644add`) so the camera
   eases in from wherever it currently is, not from the fresh aim point.
3. **Aim-point update** (every frame, stick-driven — see algorithm below).
4. **Goal angles:** `dir = normalize(s3DSFreeAimPoint - T)` (guard
   `Magnitude() > 0.01f`, else keep previous `dir`); goal
   `Beta = GetATanOfXY(T.x - P.x, T.y - P.y)` in this function's existing
   convention, goal `Alpha = Asin(Clamp(dir.z, -1, 1))`. Ease current
   `Alpha`/`Beta` toward the goal with the existing `0.1f*dt` step clamp
   (reused, not reintroduced). **No 3DS-specific `Alpha` clamp.** The
   generic post-clamp `[-89.5°, +45°]` safety bound (the non-3DS branch)
   remains as the only bound, since `atan2`/`asin` can't produce anything
   the aim-point geometry wouldn't already keep sane, but a bound must
   survive for degenerate geometry.
5. **Placement:** unchanged — `Source = T - Front*CamDist`. The reticle at
   screen centre is now a ray from `Source` through `T` toward the aim
   point, so what's under the reticle is what a shot along that ray would
   hit.

### Aim-point update algorithm (PS2 fn VA `0x34a680`, dt-scaled)

`sx, sy` = `LookAroundLeftRight()`, `LookAroundUpDown()` (reused, not raw
pad state — this inherits the existing verified sign/invert-look handling).
`k = CTimer::ms_fTimeStep * 0.6f` (PS2's constants are per-frame at its
fixed ~30 fps; reLCS's `ms_fTimeStep` is in 50 Hz units, so `k` rescales
PS2's per-frame constants to reLCS's `dt` convention while keeping the
literal PS2 magic numbers unchanged in code).

Angle helper `ang(v) = RADTODEG(Acos(Clamp((v - pedPos).z / (v - pedPos).Magnitude(), -1, 1)))`
— PS2 measures this in the ped's local frame via `PedInv * P`, but since the
ped matrix is a pure Z rotation, the z component is frame-invariant, so this
reduces to a world-space computation.

1. **Vertical:** `Pn = P; Pn.z += sy * (P - T).Magnitude() * (1.0f/3000.0f) * k;`
   accept (`P = Pn`) if `50.0f <= ang(Pn) <= 110.0f`, or if outside the band
   but `ang(Pn)` is closer to the band than `ang(P)` was (hysteresis, both
   directions).
2. **Yaw:** rotate `dir = normalize(P - T)` about world Z by
   `sx * 3.0e-4f * k` radians (PS2 rotates about the camera's local Z, which
   here is only translated, never tilted, so it's equivalent to world Z);
   `P2 = T + dir' * range`; `rel = LimitRadianAngle(GetATanOfXY(dir'.x, dir'.y) - GetATanOfXY(fwd.x, fwd.y))`.
   Accept (`P = P2`, `s3DSFreeAimPrevYawRel = rel`) if `|rel| <= DEGTORAD(110.0f)`,
   or if outside the cone but `|rel|` is smaller than `|s3DSFreeAimPrevYawRel|`
   (hysteresis).
3. **LOS snap:** `CWorld::ProcessLineOfSight(T, P, colPt, ent, true, true, true, true, false, false, false)`;
   if hit, `ent != player`, and `45.0f <= ang(P) <= 124.0f`: `P = colPt.point`.

Step 2 re-projects `P` to `range` from `T` every frame, so an LOS-snapped
point (step 3) is pushed back to full range and re-snapped next frame —
this is PS2's actual behavior (confirmed in disassembly), not an
approximation, and is why the vertical step's `(P-T).Magnitude()` factor
keeps shrinking near obstacles. Keep it as-is.

### Why this fixes both symptoms without further offset

The shoulder offset (`T` moved right and up relative to `pedPos`) is what
makes the reticle no longer coincide with the head — the camera orbits a
point beside the ped, not the ped's own position. The pitch fix is
emergent, not a wider clamp: the envelope still bounds the aim point
relative to the ped's hip, but the camera derives its own pitch from a
different, closer pivot (`T`), so the same envelope allows steeper camera
angles once the aim point is near nearby geometry — reproducing PS2's ~−60°
without a hand-picked wider number.

## Explicitly out of scope (considered, rejected)

- **Camera distance-table constants** (PS2 VA `0x393898`: base 2.5 /
  angleDist 1.6 or 0.7 / falloff 1.0 vs reLCS's `fBaseDist=1.7f` /
  `fAngleDist=2.0f` / `fFalloff=3.0f`). Different tuning question, not
  reported as a defect; changing it would also affect normal `MODE_FOLLOWPED`
  distance behavior outside free aim in ways not requested.
- **Arm-hang at extreme pitch.** PS2's arm visibly drops out of the aim pose
  when the aim point can't be reached; reLCS's `PedIK.cpp` limb limits
  (torso ±45° pitch, arm ±70°) will simply saturate at those bounds instead.
  Accepted deviation — building PS2's arm-drop animation logic is out of
  scope for this fix.
- **`CVector` vs `CEntity` dummy aim point.** PS2 attaches a real dummy
  entity via `SetPointGunAt` so other systems (e.g. auto-aim assist,
  `m_pPointGunAt` readers) can see it. No such reader exists on the 3DS
  free-aim path today; a `CVector` is sufficient and smaller.

## Verification

No 3DS console available for this change. Verification is limited to:

```sh
python3 -m unittest discover -s scripts/tests -p 'test_*.py'
scripts/verify-layout.sh
scripts/build.sh relcs
```

New test `scripts/tests/test_3ds_free_aim_point.py`: the aim-point update
(steps 1–2 of the per-frame algorithm above, sans the LOS snap, which needs
world geometry) extracted into a standalone static function taking plain
`CVector`/`float` arguments, compiled with the host `c++` against a stub
`CVector`, asserting:

- full-down stick from level converges and stops at `ang(P) == 110°`;
- from the floor, stick-up moves `P` back toward the band (hysteresis);
- yaw stops at `|rel| == 110°` from forward and re-enters on reverse input;
- `|P - T| == range` after every accepted yaw step;
- `dt == 0` is a no-op.

The existing `test_3ds_free_aim_latch.py` is unaffected (latch state
machine, not touched by this change). On-device check (when hardware is
available): compare max-down free aim and reticle offset against
`ps2_down_pitch.png`.

## Accepted residual risks (no hardware to verify)

- The `k = ms_fTimeStep * 0.6f` per-frame→dt rescale is a best-effort
  mapping of PS2's fixed-30fps constants into reLCS's variable-timestep
  convention; the exact feel (how fast the aim point tracks the stick) may
  need an on-device tuning pass, though the envelope/cone/LOS bounds are
  exact regardless of `k`.
- The yaw rotation is applied in world XY instead of the camera's local Z
  plane; these are equivalent only because the camera matrix here is never
  tilted before use (verified in the PS2 disassembly for this call site,
  not a general property of `CMatrix`) — if a future change tilts the
  camera matrix before this computation, this equivalence would need
  re-checking.
