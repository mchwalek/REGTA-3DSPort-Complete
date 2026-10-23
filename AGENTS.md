# AGENTS.md

Agent-facing operational notes for this repo. This file does **not** duplicate
`README.md` — read that first for project background, supported hardware,
data preparation, and full CIA-packaging docs. This file only covers what an
agent tends to get wrong.

## Orientation

- Three parallel game trees, each a full GTA game ported to 3DS:
  `III/` (re3, GTA III), `miami/` (reVC, Vice City), `stories/` (reLCS,
  Liberty City Stories). **`stories/` is the primary 3DS target** — it's the
  only tree with 3DS-only additions like `src/core/BottomScreen3DS.{cpp,h}`
  and the `CPad::Gui*` input helper layer in `src/core/Pad.h`.
- Naming is inconsistent by design for Vice City: source tree is `miami/`,
  binary is `miami.3dsx`, installed on the SD card as `revc.3dsx`, and SD
  data lives under `/3ds/miami/`. Don't "fix" this — it's load-bearing.
- `stories/src/renderer/` is what `III/src/render/` and `miami/src/render/`
  are called in the other two trees. Same content, different name.
- `common/` holds code shared by all three: `librw` (RenderWare replacement,
  including the 3DS PICA200 backend in `librw/src/3ds/`), `libctru`,
  `citro3d`, `mpg123-ctr`, `openal-soft-ctr` (all locally patched — see
  Landmines). `{III,miami,stories}/vendor/*` are **symlinks** into `common/`,
  so editing `common/librw/...` affects all three games at once.
- Only `stories/src/core/config.h` has `_3DS`/`GTA_HANDHELD` conditionals.
  `III/src/core/config.h` and `miami/src/core/config.h` have none — their
  3DS behavior comes entirely from makefile `-D` flags and per-file
  `#ifdef _3DS` blocks. Don't assume a config.h change in one tree applies
  to another.

## Build

The vendored toolchain in this workspace is **not** at the default
`/opt/devkitpro` location. `$WORKSPACE_ROOT` is the parent directory
containing `repo/`, `sdk-r55/`, and `hosttools/` (set it in your shell,
not in this repo). Export before building:

```sh
export DEVKITPRO=$WORKSPACE_ROOT/sdk-r55
export DEVKITARM=$DEVKITPRO/devkitARM
export PATH="$DEVKITARM/bin:$DEVKITPRO/tools/bin:$PATH"
```

Toolchain is hard-pinned by `common/devkitarm-r55.mk`: it errors unless
`arm-none-eabi-gcc` reports exactly `10.2.0` **and** `devkitARM release 55`.

Build one game with `scripts/build.sh [re3|revc|relcs]` (also accepts
`all`, and aliases `iii`/`vc`/`lcs`). It passes the correct flag set per
tree automatically — **don't call `make` directly** unless you also pass
identical flags. All three trees fingerprint their object directory by the
exact `-D` flag set (`PREFIX := ./obj/$(FINGERPRINT)/`, an md5 of the
concatenated config strings, identical scheme in `III`/`miami`/`stories`),
so different flags can't silently reuse another build's objects — but the
*final* `relcs.elf`/`.3dsx` filename is not fingerprinted. A bare `make -C
<tree>/build -f GNUmakefile` with no flags builds a flag-incomplete-but-
internally-consistent object set into a different `obj/<fingerprint>/` and
silently overwrites the real binary with one missing the 3DS feature flags.
If in doubt, `make -C <tree>/build -f GNUmakefile clean` first.

To compile a single file for a quick syntax check, discover the real
fingerprinted object path for your flags with `object-info` first — there
is no make rule for a flat `obj/src/...` path:

```sh
make -C stories/build -f GNUmakefile \
  LOADING_PIPELINE=1 BOTTOM_LOADING=1 BOTTOM_RADAR=1 \
  object-info | grep BottomScreen3DS
# ->	 ./obj/<fingerprint>/src/core/BottomScreen3DS.o

make -C stories/build -f GNUmakefile \
  LOADING_PIPELINE=1 BOTTOM_LOADING=1 BOTTOM_RADAR=1 \
  obj/<fingerprint>/src/core/BottomScreen3DS.o
```

(match the flags `scripts/build.sh relcs` uses; see that script for the
exact set per game). Add `-n` to the second command to see the compiler
invocation without running it.

Outputs land in `<tree>/build/`: `relcs.elf`, `relcs.3dsx`, `relcs.lst`,
and a map file literally named `.map`. None of these are checked in.

Package a `.cia`/`.3dsx` for a built game with `scripts/package-cia.sh
[re3|revc|relcs ...]` (same aliases as `build.sh`; no args packages all
three, each requiring its own ELF already built). It wraps
`packaging/production_cia/build_production.sh` with `BANNERTOOL`/`MAKEROM`/
`THREEDSXTOOL` defaulted to the vendored `hosttools/`/`sdk-r55/` locations —
see the `relcs-3ds-build` skill for details and the known-good sha256 to
sanity-check packaging still works.

Deploy a built `.3dsx` to a real 3DS over the network with
`scripts/deploy.sh <re3|revc|relcs> [3ds-ip]` (`3ds-ip` defaults to
`$N3DS_IP`). The console must already be sitting in Homebrew Launcher
waiting for a connection — see landmine #14 below for a capture artifact to
not mistake for a failed transfer.

## Landmines

1. **Never run a bare `git add -A` / `git add .`.** `sdstage/` is a local SD
   staging directory that can contain hundreds of MB of copyrighted game
   data (`.img`, `sfx.RAW`, `.TXD`, `.IFP`, `.COL`, etc.). It's gitignored,
   but double-check `git status --short` before any broad `git add`.
2. **`.gitmodules` in `III/`, `miami/`, `stories/` are vestigial.** Nothing
   is registered in `.git/config` and `vendor/librw` is a symlink, not a
   gitlink. Do not run `git submodule update --init` — it does nothing
   useful.
3. **Generated files — never hand-edit:**
   - `*/src/extras/GitSHA1.cpp` — regenerated by `printHash.sh` on every
     `make` invocation (only `GitSHA1.cpp.in`/`GitSHA1.h` are tracked).
   - `obj/**/default.shbin`, `*_shbin.h` — produced by `build/shlist.sh`
     calling `picasso`. Edit `common/librw/src/3ds/shaders/*.v.pica` and
     `default.shlist` instead.
   - `*_bin.h` headers — produced by `bin2s` from the `.bin` sources in
     `src/core/`/`src/renderer/`. Edit the `.bin` files instead.
   - `*.menu3ds-v1[.tmp]` — texture caches generated on-console at
     runtime (`common/3ds/MenuCacheIO.h`).
4. **Dead build machinery — do not "fix" or extend it:** `premake5.lua`,
   `CMakeLists.txt`, `cmake/`, `conanfile.py`, `codewarrior/`, `.vscode/`,
   per-tree `.github/workflows/`, `common/librw-stereo/` (a stale fork,
   never selected by `scripts/build.sh`). The only real build entry point
   is `<tree>/build/GNUmakefile`.
5. **`gamefiles/` overrides need two edits kept in sync.** Root
   `.gitignore` ignores `/gamefiles/**` then re-allows an explicit list of
   ~20 files. `scripts/setup-game.sh` has a matching hardcoded allow-list
   of what it copies from `gamefiles/<game>/`. Adding a new runtime
   override requires editing **both**. Same pattern for
   `/packaging/prebuilt/**`.
6. **Vendored libs in `common/{libctru,citro3d,mpg123-ctr,openal-soft-ctr}`
   are locally patched.** Do not replace with upstream/prebuilt versions.
7. **`CTheScripts::LoadAllScripts` reverses script execution order — shared
   by all three trees.** `SaveAllScripts` walks `pActiveScripts` head→tail;
   `LoadAllScripts` restores each record via `StartNewScript`, which
   head-inserts (`AddScriptToList`) — every save/load round-trip reverses
   the list, and parity alternates each cycle. PS2 has no equivalent restore
   step at all (it rebuilds the list from scratch via main.scm's bootstrap
   on every load, disassembly-confirmed). reLCS fixed this in
   `stories/src/control/Script5.cpp` (`SortScriptListByCreationOrder`,
   restoring descending `CRunningScript::m_nId` order after the restore
   loop) because it caused an intermittent TR1 mission mis-spawn — see
   `git log --grep=TR1`. `III`/`miami` have the identical unfixed bug.
8. **`CTxdStore::LoadTxd(int, const char*)` retries forever on a missing
   file — it hard-locks the whole console, not just the app.** It wraps
   `RwStreamOpen` in `do { ... } while (stream == nil);` with no backoff or
   limit (`stories/src/rw/TxdStore.cpp`, shared pattern in `III`/`miami`
   too). This is fine for the handful of built-in TXDs guaranteed to exist,
   but loading any *new*, possibly-not-yet-staged TXD through it (e.g. a
   3DS-port-added asset the SD card might not have yet — deploying a
   `.3dsx` over `3dslink` does **not** push new SD card files, only the
   executable) spins forever with no way to recover except a hardware reset.
   Guard any new/optional `LoadTxd`/`LoadAtomicFile2Return` call with a
   `CFileMgr::OpenFile(path)` existence check first (see
   `CFont::LoadButtons`, `stories/src/renderer/Font.cpp:186-214`, for the
   established pattern) — never call `LoadTxd` on a path you haven't
   independently confirmed exists. See `git log --grep="console hang"`.
9. **`CPad::Mode` (0-3, the in-game Controller Settings control scheme) is
   reachable on 3DS and remaps which physical button some `CPad` accessors
   read — shared by all three trees.** `GAMEPAD_MENU` (which exposes
   `MENUACTION_CTRLCONFIG`, letting the player cycle `Mode`) is defined
   whenever `GTA_HANDHELD` is defined, and `_3DS` always defines
   `GTA_HANDHELD` — so this isn't dead PC-only menu code. `CPad::GetTarget()`
   for example reads `RightShoulder1` (R) in Modes 0/1/2 but
   `LeftShoulder1` (L) in Mode 3. New pad logic that combines a semantic
   query like `GetTarget()` with a raw check on a *different* button can
   collapse onto the same button in Mode 3 with no compile-time signal —
   this shipped as a real bug in the 3DS free-aim latch
   (`stories/src/core/Pad.cpp`'s `Update3DSFreeAim`, fixed by an explicit
    `CURMODE != 3` guard; see `git log --grep="CURMODE 3"` and the
    `gta-3ds-input-mapping` skill). Test any new multi-button pad logic
    against all 4 `CURMODE` values, not just the default.
10. **`CCam::Beta`'s sign convention is not the same across every on-foot
    camera mode — shared by all three trees (only exercised on 3DS via
    reLCS's free aim).** `Process_FollowPed`/`Process_FollowPedWithMouse`
    (`stories/src/core/Cam.cpp`) both use "Beta = direction Target→Source"
    (`Front.x = Cos(Alpha)*-Cos(Beta)`, `Source = TargetCoors - Front*CamDist`).
    `Process_FollowPed_Rotation` — active whenever the player has the
    Display→FreeCam option on — uses the *opposite* convention, "Beta =
    direction Source→Target" (`Beta = GetATanOfXY(-Dist.x, -Dist.y)` where
    `Dist = Source - TargetCoors`). Carrying a raw `Beta` value across a
    `Cam.cpp:184-198`-style dispatch switch between these modes (e.g. on a
    `MODE_FOLLOWPED`→`MODE_FOLLOWPED` transition with no `ResetStatics`,
    which the dispatch alone doesn't guard against) is silently 180° wrong.
    This shipped as a real bug in the 3DS free-aim camera's "turn toward the
    player's facing direction" entry easing, symptom was an entry angle that
    was sometimes correct and sometimes an instant 180°-off snap depending
    on which camera mode was active the previous frame — fixed by
    re-deriving the starting `Beta` from world geometry
    (    `GetATanOfXY(Source.x - TargetCoors.x, Source.y - TargetCoors.y)`,
    convention-independent) instead of trusting the inherited value; see
    `git log --grep="camera's true yaw"`. Never carry a `CCam::Beta`/`Alpha`
    value across a camera-mode dispatch switch without checking both modes'
    conventions match.

    As of the PS2-on-foot-camera parity port (see
    `docs/superpowers/specs/2026-10-16-ps2-on-foot-camera-design.md`), `_3DS`
    builds route `MODE_FOLLOWPED` exclusively to `Process_FollowPed_Rotation`
    (Target->Source convention, matching `Process_FollowPedWithMouse`), so
    the two on-foot cameras reachable on `_3DS` now agree and this specific
    mismatch is retired for `_3DS`. Non-`_3DS` builds still dispatch to the
    unmodified `Process_FollowPed` (Source->Target convention) and keep the
    original hazard -- the general rule above still applies there, and to
    any future `_3DS` camera mode added to the dispatch switch.
11. **A new `CWorld::ProcessLineOfSight` ray placed near the player ped's own
    body will self-collide with the player unless explicitly excluded —
    shared by all three trees, but only exercised on 3DS so far (the free-aim
    camera pivot).** `CPed::bUsesCollision` defaults `true`
    (`Ped.cpp`/`PlayerPed.cpp`), and `ProcessLineOfSightSectorList`
    (`stories/src/core/World.cpp`) tests every in-sector ped against the ray,
    including the player, unless the ray call excludes it — either by
    bracketing the call with `CWorld::pIgnoreEntity = entity; ...; ... = nil;`
    (the established pattern, used e.g. `stories/src/core/Cam.cpp:1607/1628`,
    `3245/3285`, `3849/3851`, `4877/4898`, `5430/5451`, and
    `Camera.cpp:1991/2004`), or by checking the returned hit entity against
    the player afterward. A ray that starts at the ped's own position and
    sweeps only ~0.5m — e.g. to offset a camera pivot sideways off the ped's
    head, or to snap a point back off nearby geometry — is exactly the
    geometry most likely to clip the ped's own raised-arm/aiming-pose
    collision model and silently collapse back onto the ped. This shipped as
    a real bug in the free-aim camera's shoulder-offset pivot (the LOS ray
    that offsets the camera pivot 0.55m along the ped's right, added in
    `stories/src/core/Cam.cpp`'s `Process_FollowPedWithMouse`, had no
    exclusion and could self-collide, silently reproducing the exact
    "reticle sits on the player's head" bug the offset exists to fix) —
    fixed by bracketing it with `CWorld::pIgnoreEntity`; see `git log
    --grep="pivot LOS ray"`. Grep for how sibling LOS calls in the same
    function handle this hazard before adding a new one, even when
    transcribing disassembly that itself never mentions the hazard — PS2's
    equivalent ray has the same self-collision risk, it's just not
    something disassembly of the *math* would ever surface.
12. **`CEntity::GetBoundRect()` / `CPhysical::GetBoundRect()` are X/Y-plane
    only — no Z, no height — identical (word-for-word for the `CPhysical`
    override) across all three trees.** `CRect` (`src/math/Rect.h`, byte-
    identical in III/miami/stories) has only `left/right/top/bottom` (x
    min/max, y min/max); `CPhysical::GetBoundRect()` is literally
    `CRect(center.x-radius, center.y-radius, center.x+radius,
    center.y+radius)` built from `GetBoundCentre()`/`GetBoundRadius()` — a
    horizontal square, not a bounding box. Any code that needs an entity's
    *vertical* extent (e.g. offsetting a marker above a vehicle's roof) must
    use `CEntity::GetColModel()->boundingBox.max.z -
    boundingBox.min.z` instead — an idiom already established at multiple
    call sites in every tree (e.g. `Entity.cpp` height calcs,
    `Physical.cpp`'s `boundingBox.GetSize()` uses). This shipped as a real
    bug in the reLCS lock-on reticle port (the vehicle marker's height
    offset was computed from `GetBoundRect()`, which for a vehicle is just
    `-2*GetBoundRadius()` — its horizontal footprint size, not its height),
    caught in code review before merge; see `git log --grep="lock-on
    reticle"`. `GetBoundRect()`'s name reads as "the entity's bounds" but it
    is scoped to X/Y only — don't reach for it when Z is what's needed.
13. **`CPed::m_fMaxHealth` (stories-only; III/miami have no such field) is
    never initialized by the ped constructor and has exactly one writer in
    the entire codebase.** `CPed::CPed` (`stories/src/peds/Ped.cpp`) sets
    `m_fHealth = 100.0f` but never touches `m_fMaxHealth`
    (`Ped.h:763`) — the only place anything ever assigns it is the
    `COMMAND_SET_CHAR_MAX_HEALTH` script opcode
    (`stories/src/control/Script9.cpp`), used for scripted mission
    characters only. Every ordinary ped (pedestrians, generic gang members,
    anything not touched by that opcode) has `m_fMaxHealth` holding
    whatever the pool slot's memory last contained — 0.0f on a fresh slot,
    or another ped's stale value on a recycled one. Any new code that reads
    `m_fMaxHealth` (e.g. `m_fHealth / m_fMaxHealth` for a health ratio) must
    guard the denominator (`maxHealth > 0.0f ? maxHealth : 100.0f`) and
    clamp the result — a raw divide risks `+Inf`/UB on the common case, not
    an edge case. This shipped as a real bug in the reLCS lock-on reticle
    port (PS2 disassembly implied the field behaves like a normal ratio
    denominator; the port's own codebase never populates it), caught in
    code review before merge; see `git log --grep="lock-on reticle"`.
14. **A captured `scripts/deploy.sh`/`3dslink` run showing progress stuck at some
    percentage (e.g. `"... sent (48.92%), 189 blocks"`) with no further
    output is expected, not evidence of a stalled/failed transfer.**
    `3dslink` renders its progress bar with carriage returns (`\r`),
    overwriting the same terminal line in place; a tool that captures output
    by snapshotting rather than rendering a live terminal can end up showing
    only one such overwritten frame even though the process went on to
    finish normally and already exited. Confirm via `pgrep -af 3dslink` — if
    no `3dslink` process is running anymore, the transfer already completed
    (or failed) and isn't still in flight; the percentage in the captured
    text means nothing once the process has exited. The only reliable way to
    know if the deploy actually worked is to ask whether the app launched on
    the console — don't re-run `scripts/deploy.sh` speculatively based on a stale
    percentage, since that risks compounding a genuinely bad console state
    if the first attempt is in fact still live (see the `relcs-3ds-build`
    skill's "Do not wrap this in a short Bash timeout" warning for why a
    half-killed transfer is worse than a slow one).
15. **`CPed::SetPointGunAt`/`CPlayerPed::RotatePlayerToTrackTarget` have
    melee-vs-gun branches that are easy to get backwards — shared by all
    three trees, but only reachable on 3DS via reLCS's melee lock-on.**
    PS2's `SetPointGunAt` (`SLES_541.35` VA `0x1ba618` in reLCS's build)
    returns immediately — no `PED_AIM_GUN` state, no `SetMoveState(PEDMOVE_STILL)`,
    no frozen aim-pose anim — whenever the weapon's `m_eWeaponFire ==
    WEAPON_FIRE_MELEE`; `RotatePlayerToTrackTarget`'s own PS2 equivalent (VA
    `0x34ce68`) only applies its ±25° body-heading clamp when the weapon
    lacks `WEAPONFLAG_CANAIM_WITHARM` (true for guns, false for every PS2
    melee weapon) **or** the ped is mid-`PED_FIGHT`. Both read like "this is
    gun-specific, melee falls through to a no-op below" at first glance, but
    the melee branch needing explicit handling is the point, not an
    afterthought — a one-line gate (`GetWeapon()->IsTypeMelee()`) is the
    whole fix in both. Getting either backwards reproduces two different-
    looking "can't move while locked on" bugs: skip the `SetPointGunAt` gate
    and the ped glues into `PED_AIM_GUN`/`PEDMOVE_STILL` until a fight move
    happens to call `EndFight`→`RestorePreviousState`; skip the
    `RotatePlayerToTrackTarget` gate and the ±25° clamp runs every frame and
    continuously yanks the stick-derived heading back toward the target, so
    the ped can only ever walk toward/into it, never away or sideways — both
    present as "frozen" to a player but have unrelated root causes requiring
    separate fixes. See `git log --grep="PED_AIM_GUN for melee"` and
    `--grep="body-tracking clamp"`.
16. **`CPed::Fight()`'s melee strike point is a fixed ped-local offset on
    PS2, not an animated bone node — shared by all three trees' fight code,
    confirmed via reLCS's `stories/src/peds/PedFight.cpp`.** PS2's `Fight()`
    strike block (`SLES_541.35` VA `0x1bed40-0x1beef4`) computes
    `touchPos = GetMatrix() * offset[hitLevel]` from a fixed 5-entry local-
    space table (`(0,0,0)` null, `(0,0.7,-1.0)` ground, `(0,0.7,0.0)` low,
    `(0,0.7,0.2)` medium, `(0,0.7,0.5)` high — always ~0.7m straight ahead of
    the ped's own matrix, height varying by hit level) — it never reads a
    bone/node position at all. Code that instead picks an *animated* bone
    node per fight move (e.g. `PED_HANDR` for a punch, `PED_FOOTR` for a
    kick) looks more "correct" by GTA-engine convention (plenty of other
    systems — ragdoll contact points, weapon fire offsets — do use bone
    nodes) but is wrong for this specific function: the strike sphere ends
    up tracking whichever hand/foot node the swing animation happens to have
    retracted at that frame, which silently whiffs attacks that use the
    "wrong" limb for their node (e.g. a left-hook move whose node mapping
    defaults to the right hand). If a melee move starts whiffing after an
    animation/move-table change, check whether the contact point is still
    using this fixed-offset table before assuming the animation or hit-
    detection radius is at fault. See `git log --grep="melee whiffing"`.
17. **Adding a field to `CPed`/`CPlayerPed` grows `sizeof()` and silently
    breaks every existing 3DS save file — shared by all three trees'
    structure, but only load-bearing on 3DS.** `COMPATIBLE_SAVES` is
    explicitly `#undef`'d for `_3DS` in `stories/src/core/config.h:499-509`
    ("Match re3/reVC on 3DS: save the native 32-bit ARM structures"), so on
    3DS `CPed`/`CPlayerPed` save/load is a raw, unversioned
    `memcpy(ptr, pPed, sizeof(CPlayerPed))` blob (save:
    `stories/src/core/Pools.cpp:546-547`, load: `:600-607`) with no size
    field and no version check — every byte after the ped block (wanted
    level, player model name, everything else in the save) is positioned
    purely by `sizeof(CPlayerPed)` matching between the binary that wrote
    the file and the binary reading it. `//VALIDATE_SIZE(CPlayerPed,
    0x5F0);` (`PlayerPed.h:123`) is commented out and `VALIDATE_SIZE` itself
    is a no-op unless `CHECK_STRUCT_SIZES` is defined (it isn't by
    default), so nothing at compile time warns you when a new field moves
    this number. This shipped as a real bug during the PS2-parity lock-on
    port: three new `CPlayerPed` instance fields
    (`m_nLockOnCooldown`/`m_bLostLockOnTarget`/`m_vecLastLockOnPos`, commit
    `9db270c`) grew `sizeof(CPlayerPed)`, and loading a save written by the
    pre-change binary hung at "loading game, please wait" on real hardware
    — the desynced blob boundary shifted every subsequent read, corrupting
    the player's model name and very plausibly driving it into the
    `CTxdStore::LoadTxd` infinite-retry hang (landmine #8). Fixed (commit
    `46e3483`) by making the three fields `static` instead of instance
    fields: `CPlayerPed` only ever has exactly one live instance per
    session (confirmed by auditing every `new CPlayerPed`/placement-new
    site — construction happens once via `COMMAND_CREATE_PLAYER`
    `SetupPlayerPed` or save-load placement-new in `CPools::LoadPedPool`;
    death/arrest respawn reuses the same pointer via
    `RestorePlayerStuffDuringResurrection`, never reconstructs it), so
    `static` storage is behaviorally identical here and adds zero bytes to
    `sizeof(CPlayerPed)`. Before adding any new field to `CPed`/`CPlayerPed`
    (or any other type that ends up inside a raw-blob save on 3DS), check
    whether the type being extended has a single-instance guarantee that
    makes `static` storage safe — if not, the field needs explicit
    save-format versioning, not a plain member add. See
    `git log --grep="save compatibility"`.
18. **`#ifdef FREE_CAM` is not a `_3DS`-only guard — `FREE_CAM` is defined
    unconditionally for every build, including non-`_3DS` — shared by all
    three trees, caught during the PS2-on-foot-camera-parity port's final
    review.** `stories/src/core/config.h:478` has a bare
    `#define FREE_CAM // Rotating cam` with no platform conditional around
    it, so `#ifdef FREE_CAM` blocks in `Cam.cpp`/`Camera.cpp` compile into
    *every* build, not just `_3DS`. Code that rewrites the body of a
    function already wrapped in `#ifdef FREE_CAM` (e.g.
    `CCam::Process_FollowPed_Rotation`) with new `_3DS`-specific behavior,
    reasoning "this function only ever runs when `_3DS` reaches it," is
    wrong — the non-`_3DS` dispatch path (`Cam.cpp`'s `MODE_FOLLOWPED` case)
    can still reach the same function whenever the player enables the
    Display→FreeCam option, with no `_3DS` guard anywhere inside. This
    shipped as a real (if currently unobservable, since this repo's
    `GNUmakefile`/`scripts/build.sh` only ever build `stories` with
    `-D_3DS`) violation during the PS2 on-foot camera port — the rewritten
    function body had no `#ifdef _3DS` of its own, silently changing what
    a hypothetical non-`_3DS` build's FreeCam option would do — caught by
    the final whole-branch review, fixed by nesting
    `#ifdef _3DS ... #else <original body> #endif` *inside* the existing
    `#ifdef FREE_CAM`. Any new platform-specific behavior added inside an
    already-`#ifdef FREE_CAM`-wrapped function needs its own explicit
    `#ifdef _3DS` (or equivalent), never assumed from the outer guard. See
    `git log --grep="gate PS2 on-foot camera"`.
19. **A missing/wrong GXT text key fails silently under `-DMASTER`, returning
    an empty string instead of a diagnostic — shared by all three trees'
    `CKeyArray::Search`, only actually tripped so far by reLCS's weapon-
    pickup swap prompt.** `stories/src/text/Text.cpp`'s `CKeyArray::Search`
    (~lines 441-449):
    ```cpp
    #ifdef MASTER
    	sprintf(errstr, "");
    #else
    	sprintf(errstr, "%s missing", key);
    #endif
    ```
    The 3DS build always defines `MASTER` (`stories/build/GNUmakefile:18`),
    so `TheText.Get("SOME_KEY")` on a key absent from the compiled GXT
    silently returns `""` — whatever consumes it (`CHud::SetHelpMessage`,
    etc.) renders nothing, with no console warning, no crash, nothing to
    grep for at runtime. This shipped as a real bug: `CPickup::Update`
    (`stories/src/control/Pickups.cpp`) was ported from Vice City and called
    `TheText.Get("PU_CF1")`/`"PU_CF3"`/`"PU_CF4"` — VC-only keys that don't
    exist in LCS's GXT (LCS has only `PU_CF`, which already carries a
    `~k~ ~PUCF~` token that resolves the right button per control mode) — so
    the weapon-pickup swap prompt never appeared. The swap itself goes
    through an unrelated code path and still worked, which is why this read
    as "missing a prompt" rather than "broken," and went unreported for a
    long time. Any new/ported `TheText.Get(...)` call must be checked
    against the actual compiled GXT key list (`AMERICAN.GXT`/`ENGLISH.GXT`,
    or `repo/sdstage/relcs/TEXT/*.GXT`) before assuming it will render —
    building with `MASTER` undefined would print `"<KEY> missing"` on
    screen and catch this instantly, but no build configuration here does
    that. See `git log --grep="weapon pickup swap prompt"`.
20. **On 3DS the in-game D-pad and Select are shared with port hotkeys —
    stories only (`CPad::AffectFrom3DS`, `stories/src/core/Pad.cpp`).**
    While a player ped exists and no menu is open, the performance/stereo
    hotkeys (`rw::c3d::handle3DSPerformanceDPad`) fire only on Select+D-pad,
    the D-pad otherwise reaches the game (walking in CURMODE 0/2), and
    `PCTempJoyState.Select` is a **one-frame press on Select release** if no
    D-pad was pressed during the hold — never a held state. New game code
    must read Select with `*JustDown`-style edges (e.g.
    `CycleCameraModeUpJustDown`), not as a held button; a held-Select check
    sees at most one frame. Moving hotkeys back onto the bare D-pad silently
    kills D-pad walking (which is how it broke before, commit `f2c4b845`).
    See `git log --grep="Select+D-pad"`.
21. **reLCS's `_3DS` on-foot camera (`CCam::Process_FollowPed_Rotation`)
    replaces `Process_FollowPed` entirely, so every input the old function
    read must be re-ported by hand.** `ForceCameraBehindPlayer()` (L in
    CURMODE 0/1) was silently dead after the switch until PS2 `0x281f50`'s
    force-behind latch was ported. Before adding a `_3DS` camera-mode
    replacement, grep the replaced function for every `CPad` query and port
    or consciously drop each one. PS2 reference for the follow cam:
    `docs/superpowers/specs/2026-10-17-ps2-follow-cam-parity-fixes-design.md`.
22. **`CAutomobile::IsOpenTopCar()` alone does not mean "roofless right now" —
    stories (and miami/VC) call sites must pair it with `CarHasRoof()` where
    PS2 does.** It returns true for every `MI_STINGER` and for a Stallion with
    both `m_aExtras` set (including "no extra chosen", `-1,-1`). PS2's
    enter-car code (`CPed::PedAnimAlignCB`, `SLES_541.35` `0x30eca8`) plays
    the jump-in anim only if `IsOpenTopCar() && !CarHasRoof()`; `CarHasRoof()`
    is true unless the handling has `HANDLING_HAS_NO_ROOF` *and* both extras
    are set (roof = component 0 = `extra1`). reLCS inherited VC's version
    without the guard, so Toni jumped over the door of roofed Stingers. Before
    adding/porting an `IsOpenTopCar()` check, look up the PS2 caller (it's a
    vtable call, `lw rX,0x10c(rY)` + `jalr`). See `git log --grep="roofed Stinger"`.
23. **`DATA/OBJECT.DAT` on the SD card is GTA III's file, not PS2 LCS's — but
    its rows match PS2's compiled table, so object-physics differences are
    code bugs, not data bugs.** The PS2 disc has no text `object.dat`; the
    table is compiled into `/CHK/PS2/GAME.DTZ` (decompressed: 0x20-byte rows
    near file offset `0x3d4890`, model names hashed, same row order as III:
    mass, turnMass, airRes, elasticity, precomputed buoyancy, uproot,
    damage multiplier, then bytes effect/response/camAvoid). Before "fixing" a
    feel-wrong object by editing `OBJECT.DAT`, compare against that table and
    then against PS2 `CObject::ObjectDamage` (`SLES_541.35` `0x221e08`, takes
    a `CColPoint *` reLCS used to drop). Real case: traffic lights stopped
    cars dead because reLCS's effect-3 case only set `bRenderDamaged` and
    kept collision; PS2 removes the light and spawns `tlight_post/walk/box1/
    box2` as temp objects. See `git log --grep="smash traffic lights"`.
24. **Raw `GetCrossJustDown()` is physical B on stories, not A.** Any
    skip/accept read must go through `CPad::GetSkipCutscene()`/`GuiSelect()`
    (`stories/src/core/Pad.h`). Scripted `MESSAGE_WAIT` skips, flyby
    cutscenes, and credits all read raw Cross and skipped on B ("Go Go
    Faggio" intro was the report). See `git log --grep="skip cutscenes"` and
    the `gta-3ds-input-mapping` skill.
25. **During reLCS's 3DS free aim, `m_pPointGunAt` is nil. On PS2 it points
    at a dummy aim entity.** PS2 free aim is lock-on with a fake target
    (`SLES_541.35` `0x34b100`), so anything that keys off `m_pPointGunAt`
    (aim pose, firing direction, body tracking, re-entering the pose after
    an attack or reload) works there automatically. reLCS uses a `CVector`
    aim point instead (`Get3DSFreeAimPoint()`, `Cam.cpp`), so each of those
    has to be ported by hand under `Is3DSFreeAimActive()`. Also,
    `ClearWeaponTarget()` on free-aim entry drops `PED_AIM_GUN`, and Toni
    loses his aim pose. See the `ps2-lcs-decompilation` skill ("free aim is
    lock-on with a dummy target") and `git log --grep="aim pose"`.
26. **reLCS ped/fight code is still largely Vice City's, and PS2 LCS compiled
    out several VC hardcodes as a compare against `-1`.** `PEDTYPE_GANG7` is
    VC's friendly Vercetti gang; in LCS it's a hostile gang (`gang13`/`gang14`).
    PS2 replaced every `m_nPedType == PEDTYPE_GANG7` player exception with
    `== -1` (never true): `ReactToAttack` `0x30e8b0`, `ReactToPointGun`
    `0x30e398`, `RegisterThreatWithGangPeds` `0x3183a0`, `InflictDamage`
    `0x1c2088`. reLCS kept them live until commit `121d215`. When a stories
    behavior special-cases a VC gang or model, look for the same `-1` pattern
    on PS2 before trusting it. Peds running away from the player is usually
    PS2-correct: `fear > 100 - attacker temper`, and `PEDSTATS.DAT` and the
    IDE stat types match PS2 exactly. See the `ps2-lcs-decompilation` skill
    ("melee fight-system parity") and `git log --grep="GANG7"`.
27. **The 3DS camera "comfort" pass in `CCamera::Process` can overwrite a
    camera's pose after `CCam::Process` runs. It exists in all three trees.**
    It was added by the 3DS port (PS2 has no such layer). In
    `stories/src/core/Camera.cpp` (~806-877) it tests the final pose with a
    LOS ray and a 0.25 m sphere. If that test is blocked, it restores
    `Cams[ActiveCam].Alpha/Beta` to their values from before `Process`.
    That reset doesn't reach a camera's own state (the free-aim point
    `s3DSFreeAimPoint`, the follow cam's `ps2FollowPedVirtFar/Near`). That
    state keeps moving, and the camera jumps to it once the check stops
    running. The on-foot follow cam and free aim pull the source onto walls
    (0-4 mm), so that check failed whenever they touched a wall and the
    stick seemed to "hit a clamp". reLCS now skips the stick-held check for
    `MODE_FOLLOWPED`. Because of that, `Process_FollowPed_Rotation` has its
    own near-plane sphere check (`ClearNearPlaneOfGeometry3DS`, `Cam.cpp`).
    The 3DS top screen is wider than PS2's 4:3, so a pulled-in source with
    the 0.9 m `DEFAULT_NEAR` plane still shows the inside of buildings. When
    a camera mode keeps state across frames, check what the comfort pass
    does to it before adding the mode. Don't remove the near-plane check
    just because PS2's follow cam has none. See
    `git log --grep="camera jump after releasing"` and `--grep="near plane
    out of walls"`.

## Where things live (`stories/src`, 21 dirs, ~533 files)

| Dir | Contents |
|---|---|
| `control/` | Mission script VM (`Script.cpp` + `Script2..Script10`, `ScriptDebug`), `Garages`, `Pickups`, `Phones`, `CarAI`/`CarCtrl`, `PathFind` |
| `core/` | Game loop (`main`, `Game`, `World`, `Streaming`, `Pools`, `Timer`), frontend (`Frontend`, `MenuScreens`, `MenuScreensCustom`), input (`Pad`, `ControllerConfig`), streaming backend (`CdStreamCTR`), `BottomScreen3DS`, `config.h`, `Radar`, `Camera`/`Cam` |
| `renderer/` | `Renderer`, `Hud`, `Font`, `Sprite`, `Particle`, `Timecycle`, `Weather`, `SpecialFX` (named `render/` in III/miami) |
| `peds/` | `CPed` + AI/fight/IK/chat/routes, `CPlayerPed`, gangs, population |
| `vehicles/` | `CVehicle` + Automobile/Bike/Boat/Heli/Plane/Train/**Ferry** (LCS-specific) |
| `audio/` | `AudioManager`/`AudioLogic`, `MusicManager`, `FinalMissionMusic` (port feature), `sampman_oal` |
| `text/` | GXT loading (`CText`), `Messages` (button-label/token text), `Pager` |
| `leeds/` | LCS-engine specifics: `CustomSoundTrack`, small-heap allocator |
| `skel/3ds/` | The 3DS platform skeleton (`3ds.cpp`, `3dsmovie.cpp`, `ctru.cpp`) |
| `animation/`, `collision/`, `modelinfo/`, `objects/`, `rw/`, `save/`, `weapons/`, `entities/`, `buildings/`, `math/`, `fakerw/`, `extras/` | Standard re3/reVC/reLCS subsystems, largely unmodified from upstream |

**There is no C++ shop UI code in any tree.** Ammu-Nation, clothes, tattoo,
barber, and kiosk menus are implemented in `main.scm` and only reach C++
through two opcode seams: `CRunningScript::GetPadState` (legacy
`IS_BUTTON_PRESSED`) and `COMMAND_GET_PAD_BUTTON_STATE` (stories-only,
`Script8.cpp`). See the `gta-3ds-input-mapping` skill for the full seam map.

## Conventions

- Tabs for indentation, `.clang-format` is authoritative (`IndentWidth: 8`,
  `ColumnLimit: 160`, brace-on-same-line for control statements). See
  `III/CODING_STYLE.md` (shared by all trees): no braces around single
  statements, `int *ptr` not `int* ptr`, use `int8/uint8/int16/...` not
  `char`/`unsigned`/win32 types.
- Commit messages use a lowercase scope prefix: `stories:`, `stories/3ds:`,
  `docs:`, etc. Look at `git log` for examples before writing one.
- New `#ifdef _3DS` blocks belong in the platform-specific seam, not
  scattered as one-off checks — follow the existing pattern of grouping
  3DS behavior at the top or bottom of a function.
- Open PRs against `origin` (the user's fork, `mchwalek/REGTA-3DSPort-Complete`),
  never `upstream` (`Epic0522/REGTA-3DSPort-Complete`, the original repo):
  `gh pr create --repo mchwalek/REGTA-3DSPort-Complete --base main`. Without
  `--repo`, `gh` may default to the upstream parent.
- When a change affects behavior in only one of the three trees, say so
  explicitly in the commit message — the trees are not kept in sync by
  default (see config.h divergence above).

## Verify

```sh
python3 -m unittest discover -s scripts/tests -p 'test_*.py'
scripts/verify-layout.sh
```

The Python suite mostly compiles small extracted fragments with the host
`c++` compiler and asserts behavior — it does not need devkitARM, except
for `test_3ds_world_and_menus.py::test_compiled_menus`, which does (export
`DEVKITARM` first). `verify-layout.sh` checks that all vendored-library
symlinks under `*/vendor/` are intact.

For anything touching 3DS button/menu semantics or the packaging/build
scripts, load the matching project skill (`.opencode/skills/`) — they carry
exact commands and known-good reference hashes.

When a reLCS behavior/constant is questionable and no existing fork has
fixed it, the original PS2 disc is the tiebreaker — see the
`ps2-lcs-decompilation` skill for ISO extraction, boot-ELF (MIPS/EE)
disassembly, `main.scm` disassembly tooling, and Ghidra pseudocode (REA MCP
`tools.rea.*` or headless). The extracted boot ELF and an analysed Ghidra
project live in `$WORKSPACE_ROOT/sre/` (outside the repo — copyrighted, never
commit); stock REA rejects the R5900 ELF until the skill's
`scripts/patch_rea_r5900.py` is applied.

When a build has crashed on-device and left a `crash_dump_*.dmp` on the SD
card, see the `decoding-3ds-crash-dumps` skill for the Luma3DS dump format,
register/fault decoding, and symbolizing the crash PC/LR against a matching
`.elf`.
