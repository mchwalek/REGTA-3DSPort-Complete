# PS2 on-foot follow camera: parity fixes (zoom cycle, yaw drift, framing, whiskers)

Follow-up to `2026-10-16-ps2-on-foot-camera-design.md` (commit `fdb5b5c`).
That port of PS2 LCS's `MODE_FOLLOWPED` camera (`SLES_541.35` VA
`0x281f50-0x283db4`, identified via `CCam::Process`'s jump table at
`0x3bbe10`) shipped with four deviations that a full re-read of the
function's Ghidra pseudocode (REA evidence
`ev_bbd4e202b76aa125f8d994a54be0f5925d6fb2ad19725c77a52b6be70d32a523`) and
of PS2 `CCamera::CamControl`'s ped-zoom block (VA `0x289f3c-0x28a274`,
evidence `ev_b06e401a184739312d11562df10950465c91a7cbc5a872774f2a36a0e7a1f9e0`)
exposed.

## Why

Two user-reported on-device symptoms:

1. **Select doesn't change camera distance while Toni stands still.** It only
   takes effect once he walks away.
2. **Camera yaw doesn't stay put when walking/running forward.** It keeps
   slewing around instead of settling behind him.

Both trace to the port, not to input handling: PS2's zoom-cycle gating in
`CamControl` is identical to reLCS `Camera.cpp:1456-1482` (no
stationary/moving condition on either side).

## Goals

Make `CCam::Process_FollowPed_Rotation`'s `_3DS` body
(`stories/src/core/Cam.cpp:4826-4973`) and the ped zoom table match PS2 for
these four points:

1. String distance: zoom-out pushes the camera out even when stationary.
2. Yaw: PS2's cam-on-a-string yaw with proportional auto-rotate, smoothed
   through `BetaSpeed`.
3. Ped zoom distances: PS2's 0.0 / 2.5 / 3.5.
4. Framing + wall steering: real `Source` placed at pitch `Alpha`; port the
   5-ray whisker wall-steer and its gating of the LOS pull-in.

## Non-goals

- Weapon-class fast-rotate latch (`iGp-0x34`, `FUN_002af250`/`FUN_00172150`).
- Pitch soft-clamp when the ped walks >90° away from the camera.
- Linear FOV ease rate, tuning row 1 (`DAT_003d8650`, 0 in EUR), the
  unidentified tail callees `FUN_00283dc0`/`FUN_00299098`.
- The 3DS comfort/preset/occlusion layers in `CCamera::Process`
  (`Camera.cpp:370-1010`), except the one line in point 2.
- Vehicle, fight, free-aim/lock-on cameras; non-`_3DS` builds.

## Anti-goals

- Any change to non-`_3DS` behaviour. All new code sits inside the existing
  `#ifdef _3DS` branch of the `#ifdef FREE_CAM`-wrapped function
  (AGENTS.md landmine 18). The zoom table change is `#ifdef _3DS`-gated.
- Carrying a `Beta` across conventions: derive the string yaw from world
  geometry with `GetATanOfXY(src.x - pivot.x, src.y - pivot.y)` (landmine 10;
  reLCS `Beta` = direction pivot→Source, kept in `[-PI, PI)`).
- Adding fields to `CPed`/`CPlayerPed` (landmine 17). `CCam`/`CCamera` are
  not raw-saved (`GenericGameStorage.cpp` writes only position and zoom
  indicators), so adding state there is safe, but file-scope statics are
  enough and match PS2 (which uses gp-relative statics for this state).

## PS2 reference (pseudocode of `0x281f50`, order as in binary)

Notation: `pivot` = averaged ped pos + (0,0,0.6); `dir(b,a) =
(-cos b cos a, -sin b cos a, sin a)`; `virtFar`/`virtNear` = two LCS-only
"virtual source" vectors at CCam `+0x220`/`+0x230` (no reLCS counterpart).
Statics: `prevMaxDist` (gp-0x70), whisker `accum` (gp-0x2c), collision
`countdown` (gp-0x28).

```
stickActive = LookLR || LookUD || button 0xa;  moving = |moveSpeed| > 0
-- whiskers (point 4) --
if(!stickActive && countdown == 0){
    start = pivot - 0.3*Front_prev
    right = normalize(Up x Front_prev) * 0.17
    for i in 0..4: ray start+(i-2)*right -> Source_prev
        counts if hit && |Source_prev - hit| > current near clip
        if counts && moving: accum += (i-2)*0.03
    allBlocked = (count == 5)
}
if(stickActive || countdown > 0) allBlocked = true
if(!allBlocked){ Beta += accum; accum *= 0.95 } else accum = 0
-- distances (point 1) --
maxDist = zoomSmooth + 2.0
floor   = (maxDist > prevMaxDist) ? maxDist : 2.0
farDist = max(maxDist, 4.0)
dist = maxDist; prevMaxDist = maxDist
-- reset --
if(ResetStatics || behind || inFront){
    Beta = behind-ped yaw (+PI if inFront); BetaSpeed = AlphaSpeed = 0
    Distance = 1000; accum/countdown/latch = 0
    virtFar  = pivot - farDist*dir(Beta, 0)
    virtNear = pivot - maxDist*dir(Beta, 0)
    Alpha = -lookDown
}
-- string --
strFront = normalize(pivot - virtFar_prev)
strDist  = |pivot - virtNear_prev|
if(strDist < maxDist && maxDist > 2.0) dist = max(strDist, floor)
-- yaw (point 2) --
yawStr = yaw of strFront; Δ = pedYaw - yawStr (wrapped)
if(|Δ| < 170°){ k = min(1, 0.1*dt*|speed|); step = clamp(k*Δ, ±0.02*dt) } else step = 0
target = wrap(yawStr + step - Beta) / max(dt, 1)            // yawStr expressed in Beta's convention
target += 0.007²*|x|*x*(1/1120)*FOV                          // stick
target = clamp(target, ±0.1)
BetaSpeed = 0.8^dt*BetaSpeed + (1-0.8^dt)*target; if |BetaSpeed| < 1e-4: 0
Beta += BetaSpeed*dt
-- pitch (unchanged from fdb5b5c except source vector) --
targetPitch = asin(strFront.z) - lookDown, clamp [-85°, 45°]
Alpha += clamp((1-0.8^dt)*(targetPitch-Alpha), ±0.1*dt)
AlphaSpeed = smoothed stick (0.6/1120); virtualPitch = targetPitch + AlphaSpeed*dt
clamp Alpha [-85°,45°]; virtualPitch += lookDown
-- pose (point 4) --
Front    = dir(Beta, Alpha)
Source   = pivot - dist*Front                  // real source: pitch Alpha, NOT Alpha+lookDown
virtFar  = pivot - farDist*dir(Beta, virtualPitch)
virtNear = pivot - dist   *dir(Beta, virtualPitch)
-- collision (point 4 gate) --
if(allBlocked){ LOS pivot->Source; on hit countdown = 2; <existing pull-in/near-clip/ped re-cast> }
countdown decremented once per frame (>0)
-- tail: unchanged --
```

Notes on reading the above:
- PS2's yaw target is "where the string points, nudged toward behind-ped",
  turned into a speed and fed through the same `0.8^dt` smoother as the stick.
  The camera therefore follows the string when the ped moves (classic
  cam-on-a-string) and only drifts behind him proportionally to the
  remaining angle, so it settles instead of slewing.
- `Front` and the real `Source` share pitch `Alpha`: the camera sits above the
  pivot and looks straight at it. `lookDown` only shapes the virtual sources,
  i.e. which pitch the string "wants" next frame.

## Changes

### 1. String distance floor (Select bug)

`PS2FollowPedStringDist` becomes a PS2 transcription taking the previous
frame's `maxDist`:

```cpp
// dist = |pivot - virtNear_prev|; returns the camera's string length.
float PS2FollowPedStringDist(float strDist, float zoomSmooth, float prevMaxDist)
{
	float maxDist = 2.0f + zoomSmooth;
	float floor = (maxDist > prevMaxDist) ? maxDist : 2.0f;
	if(strDist < maxDist && maxDist > 2.0f)
		return Max(strDist, floor);
	return maxDist;
}
```

`prevMaxDist` is a file-scope static updated every frame after the call.
`strDist` is measured to `virtNear` (point 2), not to the collision-adjusted
real `Source`, so a wall pull-in no longer shrinks the string.

### 2. String yaw (yaw drift)

- New file-scope statics `ps2FollowPedVirtFar`, `ps2FollowPedVirtNear`
  (CVector), initialised in the reset block exactly as above.
- `PS2FollowPedAutoRotateStep(betaDelta, pedSpeed, dt)` becomes proportional:
  `if(|Δ| >= 170°) 0; k = Min(1, 0.1*dt*|speed|); return clamp(k*Δ, ±0.02*dt)`.
  The old `speed² <= 0.001` / `|Δ| < 0.01` early-outs go: `k*Δ` is already ~0
  there. (PS2's 170° gate moves inside the helper.)
- Yaw step in the function:
  `stringBeta = GetATanOfXY(virtFar.x - pivot.x, virtFar.y - pivot.y)`;
  `Δ = wrap(behindBeta - stringBeta)`;
  `goal = wrap(stringBeta + AutoRotateStep(Δ) - Beta)`;
  `targetSpeed = goal / Max(dt, 1.0f) + stick term`, then the existing
  `PS2FollowPedStickSpeed` smoothing/clamp/snap generalised to take this
  `targetSpeed` instead of computing the stick term itself (new signature
  `PS2FollowPedSpeedStep(float target, float prevSpeed, float dt)`; the stick
  quadratic stays a separate one-line helper so the pitch path keeps using it).
  `Beta += BetaSpeed*dt`, wrap.
- Pitch target uses `strFront = normalize(pivot - virtFar)` instead of the
  real `Source` (drops fdb5b5c's deliberate deviation — with the real Source
  now at pitch `Alpha`, using it would make `targetPitch` chase itself down
  by `lookDown` every frame).
- `Camera.cpp:526-531`: remove the `_3DS` zeroing of `BetaSpeed`/`AlphaSpeed`
  on stick release (PS2 decays them at `0.8^dt`; with yaw now flowing through
  `BetaSpeed`, zeroing would hitch the auto-rotate every release). Keep
  `orbitBeta3DS`/`orbitAlpha3DS`.

### 3. Ped zoom values

`Camera.cpp:1526-1531`: under `#ifdef _3DS`, `m_fPedZoomValue = 0.0f / 2.5f
/ 3.5f` for `CAM_ZOOM_1/2/3` (PS2 `0x289f3c-0x28a274`). String lengths become
2.0 / 4.5 / 5.5 m. Non-`_3DS` keeps 0.25/1.5/2.9. The existing
`PedZoomIndicator == CAM_ZOOM_3 && m_fPedZoomValue == 0` special case at
`Camera.cpp:1560` is unchanged (PS2 has it too). The PS2-only
"ped state 0x3a + vehicle model 0xa2 → 3.5" override is not ported.

### 4. Framing + whiskers

- Pose: `Source = TargetCoors - Front*CamDist` (pitch `Alpha`); delete the
  `sourcePitch` vector. Reset sets `Source` the same way.
- Whiskers, before the distance step, with file-scope statics
  `ps2FollowPedWhiskerAccum` (float) and `ps2FollowPedCollisionCountdown`
  (int), zeroed on reset:
  - Skip when stick deflected (`LookAroundLeftRight/UpDown != 0`; PS2 also
    tests pad button 0xa — map to nothing, see builder notes) or
    `countdown > 0`.
  - 5 `CWorld::ProcessLineOfSight` rays with the same flags as the step-10
    LOS, bracketed by `CWorld::pIgnoreEntity = CamTargetEntity` (landmine 11).
    "Current near clip" = `RwCameraGetNearClipPlane(Scene.camera)`.
  - `allBlocked`/`accum` exactly as the PS2 block above; `moving` =
    `pedSpeed > 0`.
- Step-10 LOS block runs only `if(allBlocked)`; on hit set `countdown = 2`.
  Decrement `countdown` once per frame when >0 (PS2 decrements at the top of
  the whisker test).

## Tests

Update `scripts/tests/test_3ds_ps2_follow_ped_cam.py` (host-compiled helper
extraction):
- `PS2FollowPedStringDist`: zoom growing (`prevMaxDist < maxDist`) with
  `strDist` at the old length returns `maxDist`; zoom shrinking returns
  `maxDist`; steady zoom keeps `strDist` within `[2, maxDist]`; `maxDist == 2`
  returns 2.
- `PS2FollowPedAutoRotateStep`: proportional (`Δ=0.01, speed 10, dt 1` →
  0.01, not 0.02); capped at `0.02*dt`; zero at speed 0; zero at |Δ| ≥ 170°.
- `PS2FollowPedSpeedStep`: smoothing/clamp/snap.
- Keep the look-down and pitch-step tests.

Build with `scripts/build.sh relcs`; run the Python suite.

## On-device acceptance

1. Stand still, press Select repeatedly: camera visibly moves through three
   distances (2.0 / 4.5 / 5.5 m) in both directions.
2. Run straight forward on open ground: camera stays behind Toni, no
   continuous swinging; turning gently pulls the camera round smoothly.
3. Release the C-stick mid-swing: rotation decays over a few frames, no hitch.
4. Walk along a wall: camera steers away from it rather than snapping in.
5. Load an existing save: no hang (no save-format change expected).

## Left to the builder

- Exact placement of the countdown decrement and whisker test relative to the
  reset block, as long as the order matches the PS2 listing above.
- PS2 pad button 0xa in `stickActive`: unidentified; treat as absent unless
  found trivially in `CPad`.
- Whether the comfort layer's obstruction fallback (`Camera.cpp:855-860`,
  rewrites `Beta`/`Alpha` to the pre-`Process` values when its own probe is
  blocked) fights the whiskers. If on-device testing shows yaw snapping back
  near walls, report it; changing that layer is out of scope here.
