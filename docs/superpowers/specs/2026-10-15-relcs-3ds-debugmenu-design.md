# reLCS 3DS debug menu (with mission select) — design

## Goal

Make the existing re3-derived debug menu (`stories/src/extras/debugmenu.cpp`)
usable on the 3DS in an opt-in debug build, primarily so a developer can launch
an arbitrary mission script from `main.scm`. The rest of the menu's tools
(cheats, car spawns, time/weather, camera) come along for free.

Scope: `stories/` only. `III/` and `miami/` are not touched.

## Non-goals

- Faking story progress. "Start mission N" launches the mission script only,
  the same as the PC debug switcher. Missions that depend on globals set by
  earlier missions may misbehave; that is accepted.
- Verifying the hard-coded mission name list against `main.scm` (no game
  data is available in the workspace to check against).
- Touch/bottom-screen UI. The menu renders on the top screen only.
- Re-enabling `RELOADABLES` (PC-oriented reload entries).

## 1. Build gating

- `scripts/build.sh relcs` accepts an opt-in `DEBUGMENU=1` (environment
  variable), forwarded to make. `stories/build/GNUmakefile` adds
  `-DRELCS_DEBUGMENU` to `RE3_CFG` when `DEBUGMENU=1`. Because the object
  directory is fingerprinted by the config flag set, debug and release objects
  never mix.
- `stories/src/core/config.h`, directly after the existing `_3DS` `#undef`
  block (`#undef DEBUGMENU / RELOADABLES / MISSION_SWITCHER`):

  ```c
  #if defined(_3DS) && defined(RELCS_DEBUGMENU)
  #define DEBUGMENU
  #define MISSION_SWITCHER
  #endif
  ```

- `MASTER` stays defined. Without `DEBUGMENU=1` the preprocessed source is
  identical to today's, so release builds are unaffected.

## 2. Pad input (inside `debugmenu.cpp`, `#ifdef _3DS`)

The menu's keyboard reads go through `KEYJUSTDOWN(k)` / `KEYDOWN(k)`. On 3DS
these become a small mapping from the `RsKeyCodes` the menu already uses to
3DS buttons, read with `hidKeysDown()` / `hidKeysHeld()`:

| Menu key | 3DS button | Menu action |
|---|---|---|
| `rsUP` / `rsDOWN` | D-pad up / down | move selection |
| `rsLEFT` / `rsRIGHT` | D-pad left / right | change value / fire command |
| `rsPGUP` / `rsPGDN` | L / R | scroll |
| `rsENTER` | A | enter submenu |
| `rsBACKSP` | B | go back |
| `rsLSHIFT` / `rsRSHIFT` | Y (held) | step by 5 |

- A on a command entry (`MENUCMD`) also fires the command (on PC commands fire
  on left/right or click).
- Toggle: Select + D-pad Up, just-pressed (either button newly pressed while
  the other is held), replaces `CTRLJUSTDOWN('M')`. When the toggle fires, the
  D-pad Up press is not also processed as menu navigation.
- The existing auto-repeat logic works unchanged on top of the mapping.
- `updateMouse()` and mouse-cursor drawing are skipped on 3DS; the mouse
  "button" variables stay 0.
- The mapping is a pure function (`RsKeyCodes` → 3DS key bitmask) so it can be
  host-tested.

## 3. Swallowing game input

- New accessor `bool DebugMenuIsOn(void)` in `debugmenu.h`.
- `CPad::AffectFrom3DS()` (`stories/src/core/Pad.cpp`), under
  `#ifdef DEBUGMENU`: if `DebugMenuIsOn()`, call `PCTempJoyState.Clear()` and
  return early — the same pattern the cheat-keyboard combo uses. The game sees
  a neutral pad; the world keeps running.
- On 3DS, `DebugMenuProcess` does **not** set
  `pad->DisablePlayerControls = 1`: nothing clears it again, so the player
  would stay frozen after the menu closes.
- Accepted side effect: the Select press of the toggle combo can reach the
  game for one frame before the menu opens.

## 4. Content and mission switcher

- `DebugMenuPopulate` (`stories/src/core/re3.cpp`) is kept as-is. Any entry or
  `#ifdef DEBUGMENU` hook elsewhere that fails to compile, or is meaningless on
  3DS (e.g. "Parse Heap"), gets an `#ifndef _3DS` guard. Every exclusion is
  listed in the commit message.
- `CTheScripts::SwitchToMission` (`stories/src/control/ScriptDebug.cpp`):
  - Remove the reVC-inherited early return
    `if (NumberOfExclusiveMissionScripts > 0 && mission <= UINT16_MAX - 2) return;`,
    which would block every normal launch when `main.scm` declares exclusive
    missions.
  - Ignore (return without doing anything) any `mission` outside
    `[0, NumberOfMissionScripts)`. The check happens before the running
    mission is failed, so a bad index has no side effects.
- `re3.cpp`: `nextMissionToSwitch` changes from `int8` to `int32` (the int8
  selector caps at 127; `MAX_NUM_MISSION_SCRIPTS` is 150). The selector's
  upper bound stays `ARRAY_SIZE(missions) - 1`; out-of-range indices against
  the real script count are rejected by `SwitchToMission`.
- Layout: on 3DS, reduce `topBorder` / `firstBorder` so more rows fit on the
  400×240 top screen.

## Testing

- `scripts/tests/test_debugmenu_3ds_keys.py`: extracts the 3DS key-mapping
  function from `debugmenu.cpp`, compiles it with host `c++` against stub
  `KEY_*` / `rs*` constants, and asserts every row of the table in section 2
  (plus "unknown key → 0").
- Build `scripts/build.sh relcs` and `DEBUGMENU=1 scripts/build.sh relcs`;
  both must link.
- Existing suite: `python3 -m unittest discover -s scripts/tests -p 'test_*.py'`.
- On hardware: open/close with Select+Up; navigate all categories; run one
  cheat entry; start a mission from free roam and while already on a mission;
  close the menu and confirm the player can move.

## Risks

- Unknown number of `DEBUGMENU` hooks/populate entries that don't compile for
  3DS; handled by per-entry `#ifndef _3DS`.
- `RtCharset` font size/readability on the 3DS top screen is unverified until
  run on hardware.
- Mission name ↔ index mapping is unverified.
- Extra memory for the menu font and entries on Old 3DS is unmeasured.
