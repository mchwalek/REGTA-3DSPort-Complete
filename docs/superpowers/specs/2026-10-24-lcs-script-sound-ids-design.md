# reLCS: PS2-parity for LCS script-sound ids and the missing eSound 204-206

Date: 2026-10-24. Scope: `stories/` only (reLCS). III/miami are untouched;
their `main.scm` files use their own numbering and are not affected.

## Intent

Reported bug (TODO.txt): "When entering ammunation a gunshot sound plays" —
every Ammu-Nation, one shot, when walking through the door.

Root cause: `main.scm` plays `ADD_ONE_OFF_SOUND x,y,z,52` / `53` at each
shop doorway (alternating per visit). reLCS decodes script-sound ids with
Vice City's `eScriptSounds` (`stories/src/audio/soundlist.h` ~211-282), where
52/53 are `SCRIPT_SOUND_BULLET_HIT_GROUND_1/2` → `SFX_BULLET_WALL_1+rand%3`
(`AudioLogic.cpp:8785-8798`). On PS2 LCS (`SLES_541.35`), ids 52/53 are the
Ammu-Nation door sounds `SFX_AMMU_AA/AB`.

The user asked for the faithful fix and an audit of every other misaligned
sound index. The audit (PS2 one-shot handler `FUN_001b1de8`, looping handler
`FUN_001b2a90`, frontend `FUN_001b32f8`, ped one-shots `FUN_001a6700`,
vehicle one-shots `FUN_001a3e98`, priority table `0x392830`, plus a scan of
every `PlayOneShot` caller in the ELF) found the items below. The user chose
to fold the non-script findings (sounds 204/206) into this change.

## Goals

1. Ammu-Nation doors play the PS2 door sound, no gunshot.
2. Every literal script-sound id in LCS's `main.scm` resolves to what PS2
   plays: 52/53 (and 54), 62/63, 66, 68/69, 71.
3. PS2's four extra `eSound` entries (204-207) exist in reLCS where PS2 uses
   them: 204 (ped crunch: chainsaw contact, player death in a vehicle),
   205 (frontend beep, script id 71), 206 (car-jack victim whoosh).
4. `OneShotPriority[]` matches PS2 byte-for-byte.
5. A host-compiled Python test pins the new enum values.

## Non-goals / anti-goals

- No change to looping script sounds (`ProcessLoopingScriptObject`): PS2's
  looping ids are already aligned with VC's enum (verified case by case).
- No change to C++ emitters that use `SCRIPT_SOUND_*` names (Phones, Weapon,
  BulletInfo, Object, Glass, Particle, MusicManager, Script2): they use the
  enum symbolically and stay correct after renumbering.
- No port of PS2 sound 203 (vehicle `SFX_CAR_HORN_TRUCK` 18000 Hz): no
  emitter exists anywhere in the PS2 ELF; it's dead. 207 has no handler.
- Don't touch III/miami. Don't grow `CWeapon`, `CPed`, `CPlayerPed`
  (`sizeof` is save-format on 3DS — AGENTS.md landmine #17).
- Don't "fix" the VC-derived names of things that are correct (e.g. keep
  `SCRIPT_SOUND_WILLIE_CARD_SWIPE` etc.); only add/renumber.

## Constraints

- Tabs, `.clang-format`, `int8/uint8` types, no braces on single statements
  (III/CODING_STYLE.md). Commit scope prefix `stories:`.
- Build: `scripts/build.sh relcs` (see AGENTS.md "Build"). Verify:
  `python3 -m unittest discover -s scripts/tests -p 'test_*.py'`.
- `cAudioScriptObject::AudioId` is saved (looping script objects). Saved
  looping ids used by `main.scm` are only 0, 1, 15, 67 (`ADD_CONTINUOUS_SOUND`
  literals) — all < 52 or unchanged in meaning, so old saves are unaffected.
- `PlayOneShot` gate `sound < SOUND_TOTAL_SOUNDS` (`AudioManager.cpp:250`)
  is why frontend 0xCD is currently dropped; raising `SOUND_TOTAL_SOUNDS`
  to 208 fixes it. Nothing is sized by `SCRIPT_SOUND_TOTAL` (grepped).
- `SFX_BANK_FRONT_END_MENU == SFX_BANK_0` on non-PS2 (`sampman.h:32`), so
  `SFX_BEEP` (bank 0) plays fine from `ProcessFrontEnd`.

## Part A — renumber `eScriptSounds` to PS2 LCS layout

File: `stories/src/audio/soundlist.h` (`enum eScriptSounds`, ~211-282).
Ids 0-51 are unchanged. From 52:

| id | new name | PS2 one-shot behaviour |
|---|---|---|
| 52 | `SCRIPT_SOUND_AMMUNATION_WELCOME_1` | `SFX_AMMU_AA`, freq 12000, vol 127, range 40, prio 1, speedMul 1.0 |
| 53 | `SCRIPT_SOUND_AMMUNATION_WELCOME_2` | `SFX_AMMU_AB`, same |
| 54 | `SCRIPT_SOUND_AMMUNATION_WELCOME_3` | `SFX_AMMU_AC`, same (unused by main.scm; add for completeness) |
| 55-61 | `SCRIPT_SOUND_C_OR_D_1..7` | freq 12000, vol 127, range 40, prio 1; samples per the list below |
| 62 | `SCRIPT_SOUND_DOCK_BA` | `SFX_DOCK_BA`, 12000, 127, 40, prio 1 |
| 63 | `SCRIPT_SOUND_DOCK_BB` | `SFX_DOCK_BB`, same |
| 64, 65 | `SCRIPT_SOUND_COLT45_1/_2` | `SFX_COLT45_LEFT`, freq 20159, vol 70, range 40, prio 1 |
| 66 | `SCRIPT_SOUND_PIZZA_THROW` | `SFX_PIZZA_THROW`, 20159, 70, 40, prio 1 |
| 67 | `SCRIPT_SOUND_R_OR_S_UNK1` | `SFX_R_OR_S_UNK1`, 20159, 70, 40, prio 1 |
| 68 | `SCRIPT_SOUND_GATE_START` | `SFX_GATE_START_CLU`, 20159, vol 100, range 70, prio 1 |
| 69 | `SCRIPT_SOUND_GATE_STOP` | `SFX_GATE_STOP_CLU`, 20159, vol 50, range 40, prio 1 |
| 70 | `SCRIPT_SOUND_FRONTEND_ENTER` | frontend only (Script2.cpp maps to `SOUND_FRONTEND_ENTER_OR_ADJUST`); no one-shot case |
| 71 | `SCRIPT_SOUND_FRONTEND_BEEP` | frontend only (→ `SOUND_FRONTEND_BEEP`); no one-shot case |
| 72-87 | existing VC tail, shifted +20: `BULLET_HIT_GROUND_1/2/3`(72-74), `BULLET_HIT_WATER`(75), `PAYPHONE_RINGING`(76), `GLASS_BREAK_L`(77), `GLASS_BREAK_S`(78), `GLASS_CRACK`(79), `GLASS_LIGHT_BREAK`(80), `BOX_DESTROYED_1`(81), `BOX_DESTROYED_2`(82), `METAL_COLLISION`(83), `TIRE_COLLISION`(84), `HIT_BALL`(85), `GUNSHELL_DROP`(86), `GUNSHELL_DROP_SOFT`(87) | existing cases, unchanged |
| 88 | `SCRIPT_SOUND_TOTAL` | |

Exact PS2 sample mapping for 55-63 (0x37-0x3f), builder must use these:
0x37→`SFX_C_OR_D_UNK_1`, 0x38→`_2`, 0x39→`_3`, 0x3a→`_4`, 0x3b→`_5`,
0x3c→`_3` (PS2 reuses 0x9d), 0x3d→`_6`, 0x3e→`SFX_DOCK_BA`, 0x3f→`SFX_DOCK_BB`.
None of 55-61, 64,
65, 67 are used by `main.scm`; they're added so the enum is PS2-complete,
and the builder may implement them with one shared case block (same
freq/vol/range) selecting the sample via a small switch or `sound - base`
arithmetic with the 0x3c exception. Keep it short.

Add the VC-derived comment style the file already uses where helpful
(e.g. `// LCS: PS2 ids 52-71 are LCS-specific; VC's tail starts at 72`).

Sanity: the only `main.scm` literal one-off ids are 0, 1, 3, 7-10, 13, 14,
19, 20, 52, 53, 62, 63, 66, 68, 69, 70, 71 (+ a likely false-positive 101);
continuous ids 0, 1, 15, 67 (67 is a looping id and PS2's looping handler
has no case 67 either — leave alone).

## Part B — new one-shot cases

File: `stories/src/audio/AudioLogic.cpp`,
`cAudioManager::ProcessOneShotScriptObject(uint8 sound)` (8646-8909).
Follow the existing case shape (see `SCRIPT_SOUND_WILLIE_CARD_SWIPE` at
8670: set `m_MaxDistance`, `m_nSampleIndex`, `m_nBankIndex = SFX_BANK_0`,
`m_nFrequency`, `m_nPriority`, `m_fSpeedMultiplier`, `m_bIs2D = FALSE`,
`SET_SOUND_REFLECTION(FALSE)`, `Vol`; the shared tail handles distance,
`ComputeVolume`, `iSound++`, reverb, queue). Add `#define`s next to the
other `SCRIPT_OBJECT_*_MAX_DIST/_VOLUME` constants (top of the file) in the
same style.

- Ammu welcome 1/2/3: sample per id, `m_nFrequency = 12000`, `Vol = 127`,
  `m_MaxDistance = 40`, `m_nPriority = 1`, `m_fSpeedMultiplier = 1.0f`.
- C_OR_D 1..7 and DOCK_BA/BB: same params as above, sample per the list.
- COLT45_1/2, PIZZA_THROW, R_OR_S_UNK1: `m_nFrequency = 20159`, `Vol = 70`,
  range 40, prio 1, speedMul 0.0f (PS2 leaves it 0 here; the Willie case
  in reLCS uses 1.0f — use 0.0f to match PS2's 0x40-0x43 block).
- GATE_START: `SFX_GATE_START_CLU`, 20159, `Vol = 100`, range 70, prio 1.
- GATE_STOP: `SFX_GATE_STOP_CLU`, 20159, `Vol = 50`, range 40, prio 1.

PS2 `SET_SOUND_REFLECTION` is off for all of these (reverb flag set in the
shared tail as today).

## Part C — `eSound` 204-207 and frontend beep

File: `stories/src/audio/soundlist.h`, `enum eSound` (ends
`SOUND_SHIRT_WIND_FLAP`(202), `SOUND_SET_203`, `SOUND_TOTAL_SOUNDS = 204`,
`SOUND_NO_SOUND = 205`). Change to:

```
SOUND_SET_203,
SOUND_PED_CRUNCH,          // 204 (LCS): chainsaw contact / player dies in a car
SOUND_FRONTEND_BEEP,       // 205 (LCS): script sound 71
SOUND_PED_CARJACKED_WHOOSH,// 206 (LCS): QUICKJACKED victim
SOUND_SET_207,             // no PS2 handler
SOUND_TOTAL_SOUNDS,        // 208
SOUND_NO_SOUND = SOUND_TOTAL_SOUNDS,
```

Names are the builder's call as long as the values are 204/205/206/207 and
`SOUND_TOTAL_SOUNDS == 208`. `SOUND_NO_SOUND` is only a sentinel
(`PedChat.cpp:82/98`, `Ped.cpp:79-80`, `AudioManager.cpp:183-186`); keep it
`>= SOUND_TOTAL_SOUNDS`.

`cAudioManager::ProcessFrontEnd()` (`AudioLogic.cpp:9217`, switch near
9349): add
```
case SOUND_FRONTEND_BEEP:
	m_sQueueSample.m_nSampleIndex = SFX_BEEP;
	break;
```
(not stereo, base frequency, default FRONTEND volume — exactly what the
default tail does; PS2 pan 63.)

`stories/src/control/Script2.cpp:764-769` (`COMMAND_ADD_ONE_OFF_SOUND`):
replace `case 0x46: // TODO ... PlayFrontEndSound(0xC4, 0)` with
`case SCRIPT_SOUND_FRONTEND_ENTER: DMAudio.PlayFrontEndSound(SOUND_FRONTEND_ENTER_OR_ADJUST, 0);`
and `case 0x47: ... (0xCD, 0)` with
`case SCRIPT_SOUND_FRONTEND_BEEP: DMAudio.PlayFrontEndSound(SOUND_FRONTEND_BEEP, 0);`
Remove the `// TODO` comments. (The existing mappings 1, 7-10, 13, 14, 16 in
that switch were cross-checked against PS2's frontend table — correct.)

## Part D — `OneShotPriority[]`

File: `stories/src/audio/AudioManager.cpp:234` (204 bytes, VC's table).
Replace with PS2's 208 bytes from `SLES_541.35` `0x392830`
(`python3 .opencode/skills/ps2-lcs-decompilation/scripts/elf_tools.py
$WORKSPACE_ROOT/sre/SLES_541.35 words 0x392830 52` and unpack, or read via
`E.D` at `E.va2off(0x392830)`). Known diffs vs current: index 31 → 0,
index 54 (`SOUND_WEAPON_SHOT_FIRED`) → 0, index 203 → 1, new 204..207 =
1, 0, 0, 0. Keep the existing layout/comment style of the table. The builder
should dump the 208 bytes and diff against the current table rather than
hand-apply these four edits, to be sure.

## Part E — sound 204, ped crunch

1. Handler. `cAudioManager::ProcessPedOneShots` (`AudioLogic.cpp:4345`)
   has no crunch case. Add `case SOUND_PED_CRUNCH:` (and, since PS2's ped
   handler also has a case for `SOUND_SPLATTER` (0xa5) which reLCS's
   `PedFight.cpp:3603/3623/3639` already emit on peds — see "left to the
   builder") with the parameters PS2 uses, which are identical to reLCS's
   vehicle `case SOUND_SPLATTER` (`AudioLogic.cpp:3578-3594`):
   `SFX_PED_CRUNCH_1/2` alternating via a static toggle, bank 0, counter 48,
   `freq = RandomDisplacement(6000) + 16000` (PS2: 16000 + rand%6000),
   prio 1, speedMul 0, range 40, `Vol = rand%20 + 55`,
   `SET_SOUND_REFLECTION(TRUE)`. Reuse the existing
   `VEHICLE_ONE_SHOT_SPLATTER_*` constants or add `PED_ONE_SHOT_CRUNCH_*`
   in the same style — builder's call.

2. Emitter: chainsaw contact. `stories/src/weapons/Weapon.cpp`,
   `CWeapon::FireMelee`, inside the `WEAPONTYPE_CHAINSAW` block (665-689),
   right after the `PARTICLE_DEBRIS2` add (line 681) and before the
   commented-out BLOODDROP:
   ```
   if (m_nChainsawCrunchTimer < 0) {
   	DMAudio.PlayOneShot(victimPed->m_audioEntityId, SOUND_PED_CRUNCH, 1.0f);
   	m_nChainsawCrunchTimer = CGeneral::GetRandomNumber() % 3;
   } else
   	m_nChainsawCrunchTimer--;
   ```
   PS2 also tests `victim->IsPed()` here (entity-type bits == 3); in reLCS
   the loop variable is already a `CPed *` from the ped pool, so the test
   is implied — omit it. The counter is a PS2 `CWeapon` field at +0x18 that
   reLCS lacks. **Do not grow `CWeapon`** (it's inside `CPed::m_weapons`,
   raw-blob saved on 3DS): add `int8 m_nChainsawCrunchTimer;` right after
   `bool m_bAddRotOffset;` in `Weapon.h:23` — it lands in the existing
   padding, `sizeof(CWeapon)` stays 0x18 (verify with a `static_assert` or
   by checking `sizeof` once in a quick host compile; a test is below).
   Initialise it to 0 in both constructors (`Weapon.h:27` default ctor and
   `CWeapon::Initialise`, `Weapon.cpp:~95-102`, next to `m_bAddRotOffset = false`).

3. Emitter: player dies in a vehicle. `stories/src/peds/Ped.cpp`,
   `CPed::SetDie` (7074-7135). PS2 adds, at the top of the function's
   body for the player ped only:
   ```
   if (this == FindPlayerPed()) {
   	if (!((CPlayerPed*)this)->m_bCanBeDamaged) return;
   	CVehicle *veh = FindPlayerVehicle();
   	if (!bIsDrowning && veh && !veh->bIsDrowning)
   		DMAudio.PlayOneShot(m_audioEntityId, SOUND_PED_CRUNCH, 1.0f);
   	Say(SOUND_PED_DAMAGE);
   }
   ```
   Place it where reLCS's `SetDie` first branches on the player (read the
   function; if it already has a `m_bCanBeDamaged` early-return for the
   player, merge into it rather than duplicating). The existing
   unconditional `Say(SOUND_PED_DEATH)` (7121) stays. PS2 flag mapping
   verified: ped flag = `CPed::bIsDrowning` (`Ped.h:552`), vehicle flag =
   `CVehicle::bIsDrowning` (`Vehicle.h:242`).

## Part F — sound 206, car-jack victim

1. Handler. `ProcessPedOneShots`: add
   `case SOUND_PED_CARJACKED_WHOOSH:` → `SFX_GOLF_CLUB_SWING`, bank 0,
   `m_nCounter = 0`, base frequency
   (`SampleManager.GetSampleBaseFrequency(SFX_GOLF_CLUB_SWING)`), range 100,
   prio 0, speedMul 0, `Vol = 127`, `m_bIs2D = FALSE`, loop 1,
   releasing-sound flag set, no reflection, no reverb. Match whatever the
   nearest existing one-off ped case does for the tail (check how other
   cases in that switch set `m_bReleasingSoundFlag`/`SET_SOUND_REVERB`).

2. Emitter. PS2 `FUN_00312d60` runs each frame for a ped being jacked out
   of a car and keys off `m_pVehicleAnim` (`animId`, `currentTime`), with a
   one-shot latch flag on the ped (PS2 `ped+0x7e0`):
   - `ANIM_STD_JACKEDCAR_RHS` and `currentTime > 0.6f` → `PlayOneShot(m_audioEntityId, SOUND_186, 3.0f)`
   - `ANIM_STD_JACKEDCAR_LO_RHS` > 1.2f, `ANIM_STD_JACKEDCAR_LHS` > 1.8f,
     `ANIM_STD_JACKEDCAR_LO_LHS` > 1.2f → `PlayOneShot(..., SOUND_187, 3.0f)`
   - `ANIM_STD_QUICKJACKED` > 1.6f → `PlayOneShot(..., SOUND_PED_CARJACKED_WHOOSH, 3.0f)`,
     `PlayOneShot(..., SOUND_STEP_START, 1.0f)`, `PlayOneShot(..., SOUND_STEP_END, 1.0f)`,
     `Say(SOUND_PED_DEFEND)`.
   Each fires once per jack (latch set when fired, cleared when the jack
   anim is set up / `m_pVehicleAnim` is reassigned).
   reLCS already has the bike version of exactly this at
   `stories/src/peds/PedAI.cpp:4097-4104` (`ANIM_BIKE_KICK → SOUND_187`,
   `ANIM_BIKE_ELBOW → SOUND_186`, 0.4 s gate) — put the car version next to
   the car-jacked victim anim handling (`PedAI.cpp:3463-3473`, `3880-3890`,
   the `BeingDraggedFromCar`/`QuickJacked` paths) using the same gating
   pattern that bike code uses for "fire once" (read how it latches; if it
   relies on `m_pVehicleAnim` being replaced, do the same). **No new
   `CPed` field** (landmine #17): if a latch is needed, reuse an existing
   per-jack state transition (the anim callback / state change) or a
   per-anim-time window check (`currentTime > t && currentTime - timeStep <= t`,
   mind landmine #30's end-of-anim margin: QUICKJACKED must be long enough
   for 1.6 s; check `ped.ifp` lengths via `AnimManager.cpp`'s loader if
   unsure — if too tight, fire on `currentTime > t` with the latch being
   "the one-shot was already queued this anim", e.g. by checking
   `m_pVehicleAnim->currentTime - m_pVehicleAnim->timeStep <= t`).

## Part G — tests

`scripts/tests/` (Python unittest, host `c++`): add one test module that
compiles a snippet including `stories/src/audio/soundlist.h` (and
`AudioSamples.h` if needed) and asserts:
`SCRIPT_SOUND_AMMUNATION_WELCOME_1 == 52`, `SCRIPT_SOUND_DOCK_BA == 62`,
`SCRIPT_SOUND_PIZZA_THROW == 66`, `SCRIPT_SOUND_GATE_START == 68`,
`SCRIPT_SOUND_GATE_STOP == 69`, `SCRIPT_SOUND_FRONTEND_BEEP == 71`,
`SCRIPT_SOUND_BULLET_HIT_GROUND_1 == 72`, `SCRIPT_SOUND_GUNSHELL_DROP_SOFT == 87`,
`SOUND_PED_CRUNCH == 204`, `SOUND_FRONTEND_BEEP == 205`,
`SOUND_PED_CARJACKED_WHOOSH == 206`, `SOUND_TOTAL_SOUNDS == 208`,
and `sizeof(CWeapon) == 24` (include `Weapon.h` with whatever minimal stubs
the existing tests use for engine headers — look at how
`scripts/tests/test_*.py` already compile fragments; if `Weapon.h` can't be
compiled standalone cheaply, assert the field offset by extracting the
struct body textually instead — builder's call). Also assert
`OneShotPriority` has 208 entries (parse `AudioManager.cpp`).

## Verification

- `scripts/build.sh relcs` builds clean.
- `python3 -m unittest discover -s scripts/tests -p 'test_*.py'` passes.
- On device: enter an Ammu-Nation — door sound, no gunshot; alternates
  AA/AB between visits. Pass a scripted gate (e.g. Portland Harbor /
  Salvatore's) — gate start/stop clunks now audible. Pizza-boy mission —
  throw sound. Menu/script beep on id 71 (one of its four script sites).
  Chainsaw a ped — periodic crunch. Die in a car — crunch + grunt. Get
  jacked out of a car — fight/whoosh sounds.

## Left to the builder

- Exact enum names (values fixed above).
- Whether C_OR_D/DOCK/COLT45/… share one case block.
- Whether to add a `ProcessPedOneShots` `case SOUND_SPLATTER` too
  (`PedFight.cpp` already emits it on peds and PS2's ped handler has a case
  0xa5 whose params were *not* decoded). Recommended: skip unless trivially
  the same as the crunch case; note it in the commit message as a follow-up.
- Where exactly in `SetDie` the player block goes.
- Latch mechanism for Part F without adding a `CPed` field.
- Commit split (suggest: A+B+D+G core renumber; C; E; F) — all on one
  branch/PR against `mchwalek/REGTA-3DSPort-Complete` `main`.

## PS2 reference (for re-checking, not required to build)

`SLES_541.35`: one-shot script handler `FUN_001b1de8`, looping `FUN_001b2a90`,
frontend `FUN_001b32f8` (case 0xcd → sample 0xd = `SFX_BEEP`), ped one-shots
`FUN_001a6700` (204 handler `0x1a816c`, 206 handler `0x1a6a50`), vehicle
one-shots `FUN_001a3e98`, `cDMAudio::PlayOneShot` `0x2a1f40`,
`cAudioManager::PlayOneShot` `0x238458`, priority table `0x392830`,
`ADD_ONE_OFF_SOUND` opcode handler `~0x20a25c`, `CWeapon::FireMelee`
`FUN_002a3360` (crunch at `0x2a4110`), `CPed::SetDie` `FUN_001e8fc0`
(crunch at `0x1e90a0`), jacked-victim anim sounds `FUN_00312d60`. PS2
sample indices equal reLCS `AudioSamples.h` values.
