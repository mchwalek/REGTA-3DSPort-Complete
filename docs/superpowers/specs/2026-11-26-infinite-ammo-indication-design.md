# Infinite ammo on the bottom-screen HUD

Trello: [Infinite ammo indication](https://trello.com/c/uSoiqjew/76-infinite-ammo-indication)

## Problem

In the side missions where Toni rides on the back of a bike and shoots
(`TP1`, `TP2`, `TS1` in `main.scm`), the 3DS bottom screen shows the ammo as
`9999-100`, and the clip number keeps jumping back to 100. The card asks how
PS2 shows infinite ammo there and guesses that PS2 shows nothing.

## What PS2 does

All facts come from the EUR disc (`SLES_541.35`, `DATA/MAIN.SCM`).

- **How the missions give infinite ammo.** Each mission calls
  `ATTACH_CHAR_TO_CAR` with a weapon, then runs
  `SET_PLAYER_CURRENT_WEAPON_AMMO_IN_CLIP 100` every frame (TP2 at script
  offset `0x78e79`, TS1 `0x7a380`, TP1 `0x7bf18`). The every-frame clip reset
  is why the clip count "gets reset".
- **How much ammo the attach gives.** PS2 `CPed::AttachPedToEntity`
  (around `0x1f0a00`) saves the current weapon and its total ammo, then calls
  `CWeapon::Initialise(weapon, 30000)` (`0x1f0aac`: `a2 = 0x7530`,
  `jal 0x2a2710`). reLCS does the same (`Ped.cpp` `GiveWeapon(weapon, 30000)`).
  Rampages also give 30000 (`Darkel.cpp`).
- **How the HUD shows it.** PS2 `CHud::Draw` (function `0x23f540`) loads
  `total = weapon+0xc` (`0x2402a0`), then at `0x240570`-`0x2405d8` skips the
  whole ammo text when any of these is true:
  1. `Min(9999, total - clip) == 9999` (`s3 = 0x270f`, `beq a0,s3`);
  2. a rampage is running (`jal 0x23b790`, `CDarkel::FrenzyOnGoing`);
  3. the weapon type is 0 (unarmed) or `0x22` (detonator);
  4. the weapon slot is below 2.

  The weapon icon is drawn before this check, so it stays on screen.

So the guess on the card is right: with 30000 rounds, PS2 draws the weapon
icon and no ammo number.

## What reLCS does now

- The top-screen ammo in `CHud::Draw` (`stories/src/renderer/Hud.cpp:616`)
  already has the PS2 gate, but `_3DS` builds compile it out
  (`#ifndef ENABLE_3DS_BOTTOM_RADAR`).
- The bottom-screen status bar (`DrawStatusBar`,
  `stories/src/core/BottomScreen3DS.cpp:335`) replaces it on 3DS. It only
  checks the slot and the detonator, so it prints `9999-100` for scripted
  infinite ammo and for rampages.

## Goal

When PS2 hides the ammo count, the bottom screen hides it as well. In every
other case the bottom screen behaves as it does now.

Non-goals: no new "infinite" symbol (PS2 has none), no change to the top-screen
HUD, ammo amounts, or the mission scripts.

## Approaches

1. **Put PS2's gate in the bottom screen (chosen).** Add a small helper in
   `BottomScreen3DS.cpp` that holds the four PS2 conditions and use it in
   `DrawStatusBar`. This change touches one file and only 3DS code.
2. **Share one helper between `Hud.cpp` and `BottomScreen3DS.cpp`.** One rule
   for both screens, but it changes `Hud.cpp` code that `_3DS` never compiles
   and adds a new `CHud` API for one caller.
3. **Draw a symbol for infinite ammo.** PS2 has no such symbol, so this
   would move away from PS2.

## Design

`BottomScreen3DS.cpp` gets:

```cpp
static bool
ShouldDrawAmmo3DS(CWeapon *weapon, CWeaponInfo *weaponInfo)
```

It returns false when `Min(9999, total - clip) == 9999`, when
`CDarkel::FrenzyOnGoing()`, when the slot is below 2, or when the weapon is
the detonator. `DrawStatusBar` calls it in place of its current slot and
detonator check. The weapon icon, clock, money and meters do not change.

A host-compiled test (`scripts/tests/test_3ds_bottom_ammo_gate.py`) extracts
the helper and checks: normal reserve, a reserve of exactly 9998 and 9999,
the 30000 attach case, a rampage, a melee weapon and the detonator.

## Rulings

- Ruling: Hide the ammo text and keep the weapon icon. Why: PS2 draws the
  icon before the ammo gate (`0x240570`). Cost if wrong: one line to revert.
- Ruling: Also hide the ammo during a rampage. Why: PS2's gate includes
  `FrenzyOnGoing` (`0x240598`), and rampages give 30000 rounds too, so they
  would show the same `9999-…`. Cost if wrong: the player loses the ammo
  count during rampages; one line to revert.
- Ruling: Keep the gate in `BottomScreen3DS.cpp` instead of sharing it with
  `Hud.cpp`. Why: the top-screen code is not compiled on 3DS, and a shared
  helper adds API for one caller. Cost if wrong: two copies of a four-line
  rule can drift.
- Ruling: Keep the 9999 clamp that the "total" form (weapons with clip size
  ≤ 1 or ≥ 1000) used to skip. Why: PS2 checks `total - clip` before it
  chooses the form, so the gate covers both forms. Cost if wrong: a weapon
  with a large real reserve would hide its count, which PS2 does too.
- Ruling: Change stories only. Why: the bottom-screen HUD exists only in
  `stories/`; III and miami have no `BottomScreen3DS`. Cost if wrong: none.
