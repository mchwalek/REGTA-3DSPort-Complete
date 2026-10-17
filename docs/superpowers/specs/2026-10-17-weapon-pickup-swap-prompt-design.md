# Weapon pickup swap prompt (reLCS)

## Problem

When the player stands on a weapon pickup whose weapon slot already holds a
different weapon, reLCS is supposed to show a help prompt ("Press L to take
this weapon...") and wait for the player to press the collect button before
swapping. The prompt never appears on 3DS; the swap still works if the
button happens to be pressed.

## Root cause

`CPickup::Update` (`stories/src/control/Pickups.cpp:391-406`) was carried
over from Vice City unchanged. It looks up three per-control-mode text keys:

```cpp
switch (CPad::GetPad(0)->Mode) {
case 0: case 1: CHud::SetHelpMessage(TheText.Get("PU_CF1"), false); break;
case 2:         CHud::SetHelpMessage(TheText.Get("PU_CF3"), false); break;
case 3:         CHud::SetHelpMessage(TheText.Get("PU_CF4"), false); break;
}
```

Vice City's GXT has `PU_CF1`/`PU_CF3`/`PU_CF4`. LCS's GXT does not — it has
exactly one key, `PU_CF`:

> `~w~Press~h~ ~k~ ~PUCF~ ~w~to take this weapon. Any weapon of the same
> type will be lost.`

The 3DS build defines `MASTER` (`stories/build/GNUmakefile:18`), so a
missing GXT key returns an empty string (`stories/src/text/Text.cpp:441-449`)
instead of a `"<key> missing"` placeholder. `CHud::SetHelpMessage` is then
called with an empty string every time, and nothing is ever drawn. The swap
button still works because button handling (`CPad::CollectPickupJustDown`,
`stories/src/core/Pad.cpp:3676-3706`) and the swap logic
(`DoesPlayerWantNewWeapon`/`GiveWeapon`) are unaffected by the missing text.

The port already maps the `~PUCF~` token used inside `PU_CF` to the correct
per-mode button (`stories/src/text/Messages.cpp:647`,
`{ "PUCF", PED_ANSWER_PHONE, -1 }`), and `CHud::SetHelpMessage` already runs
`InsertPlayerControlKeysInString` (`stories/src/renderer/Hud.cpp:2297`), so
a single `TheText.Get("PU_CF")` call renders the right button in every
control mode without any switch.

## PS2 ground truth

Disassembly of the EUR boot ELF (`SLES_541.35`) confirms this. The only
occurrence of a `"PU_CF"`-prefixed string in the binary is `"PU_CF\0"` at VA
`0x3d4d38`; there is no `PU_CF1`/`PU_CF3`/`PU_CF4` anywhere. Its only code
reference is inside `CPickup::Update` (function starts at `0x1c7758`):

```
1c8010  bnez (flag bit)        ; already shown this visit -> skip
1c8058  jal 0x333038 (TheText,"PU_CF")   ; TheText.Get
1c806c  jal 0x23f068 (text,0,0,1)        ; CHud::SetHelpMessage(text, quick=0, forever=0, addToBrief=1)
1c8074  sd  (set flag bit)
```

PS2 makes exactly one `TheText.Get`/`SetHelpMessage` call, gated by a
once-per-visit flag bit on the pickup — the same role as the port's
`m_bWasControlMessageShown`. PS2's `SetHelpMessage` takes a fourth
"add to previous-brief history" argument the port's 3-argument
`SetHelpMessage` doesn't have; other existing call sites in this codebase
already drop that argument when porting (e.g.
`stories/src/control/Script.cpp:476`), so `SetHelpMessage(text, false)`
matches existing convention.

PS2 additionally clears the prompt with `SetHelpMessage(nil, false)` in two
places, both gated on the same flag bit (so it's a no-op if the prompt was
never shown):

- as soon as `CollectPickupBuffer` becomes nonzero (the collect button was
  just pressed) — PS2 VA `0x1c8094`;
- when the player steps off the pickup (the `else` branch that currently
  only resets `m_bWasControlMessageShown`) — PS2 VA `0x1c80d8`.

The port only resets the flag in both cases; it never clears the message
itself, so the prompt lingers for its normal fade-out timeout after the
player leaves or swaps.

## Fix

All changes are in `stories/src/control/Pickups.cpp` only. `miami/`
(Vice City) is untouched — its GXT genuinely has `PU_CF1`/`PU_CF3`/`PU_CF4`,
so its existing switch is correct for that game.

1. **Show the prompt.** Replace the `switch (CPad::GetPad(0)->Mode)` block
   (lines 391-406) with a single call:
   ```cpp
   if (!m_bWasControlMessageShown) {
       CHud::SetHelpMessage(TheText.Get("PU_CF"), false);
       m_bWasControlMessageShown = true;
   }
   ```

2. **Clear the prompt when the collect button is pressed.** In the branch
   that currently just does `if (CollectPickupBuffer == 0) isPickupTouched
   = false;` (line 409-410), when `CollectPickupBuffer != 0` (button was
   just registered) and `m_bWasControlMessageShown` is true, call
   `CHud::SetHelpMessage(nil, false)` before the swap proceeds. This matches
   PS2 VA `0x1c8094`.

3. **Clear the prompt when the player steps off the pickup.** At the
   existing `else m_bWasControlMessageShown = false;` branch (line 419),
   call `CHud::SetHelpMessage(nil, false)` first if the flag was set, then
   reset the flag. This matches PS2 VA `0x1c80d8`. `SetHelpMessage(nil, …)`
   is already an established, safe pattern elsewhere in this file
   (`Pickups.cpp:548`).

## Out of scope

Two minor PS2 deltas turned up during disassembly that are unrelated to the
missing prompt and are explicitly not part of this fix:

- PS2 skips the 1500 ms `m_nPadDownPressedInMilliseconds` guard on the
  empty-ammo-slot auto-pickup path; the port applies it there too.
- PS2 allows four specific pickup models to bypass the "frenzy in progress"
  block; the port's `FrenzyOnGoing()` check has no exceptions.

## Testing

No practical host-side unit test exists for this: `CPickup::Update` depends
on the full engine runtime and the GXT text file, which is copyrighted and
not checked into this repo.

Verification is build + on-device:
1. `scripts/build.sh relcs`, deploy with `scripts/deploy.sh relcs <ip>`.
2. In each of the 4 control modes (`CPad::Mode` 0-3, via Controller Settings
   in the pause menu), walk onto a weapon pickup whose slot holds a
   different weapon of the same type:
   - the prompt appears, showing the correct button for that mode;
   - pressing the button swaps the weapon and the prompt disappears
     immediately;
   - walking off the pickup without pressing the button makes the prompt
     disappear immediately instead of fading out later.
