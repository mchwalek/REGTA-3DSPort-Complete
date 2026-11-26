# Scooter Shooter SMG ammo: restore PS2's 9999 cap in CPed::GiveWeapon

Trello: [Got infinite smg ammo after one of on-motorcycle side missions](https://trello.com/c/R7OqW7sM/75-got-infinite-smg-ammo-after-one-of-on-motorcycle-side-missions)

## Problem

After a few attempts of a bike rail-shooter side mission, the player's SMG
shows no ammo count and never runs out. The reporter saw ammo go up on each
attempt but had no reliable repro.

## What the missions do

The three bike rail shooters in `main.scm` are `TP1`, `TP2` (Scooter Shooter)
and `TS1`. They all do the same thing. Here is `TP2`:

1. `GET_CHAR_WEAPON_IN_SLOT L2 6 L75 L76 L77` saves the type and ammo of
   script slot 6, which is C++ slot 5 (SMG). `TS1` saves slot 8, the heavy
   weapon slot.
2. `ATTACH_CHAR_TO_CAR ... 22` puts Toni on the back of the Faggio with a
   TEC9 (`TP1` uses 24, `TS1` uses 32 M60).
3. At the end, pass or fail: `DETACH`, `ATTACH ... 0`, `DETACH`.
4. `GIVE_WEAPON_TO_PLAYER $536 L75 L76` gives back the saved weapon and ammo.

`GIVE_WEAPON_TO_PLAYER` adds ammo. If the attach/detach pair has already put
the saved weapon back (it does when the SMG was the selected weapon when the
mission started), step 4 doubles the SMG ammo. 200 becomes 400, then 800, and
so on.

## PS2 behaviour

The doubling is in the original game. Players have documented it for PS2,
PSP and mobile:

- [GTAForums, "Ammo duplication glitch"](https://gtaforums.com/topic/1004186-ammo-duplication-glitch/):
  "Micro SMG ammo can be doubled everytime you start Scooter Shooter",
  holding the Micro SMG when you get on the Faggio.
- [sundar's PSP secrets FAQ, 1.1 Double Ammunition](https://gamefaqs.gamespot.com/psp/925776-grand-theft-auto-liberty-city-stories/faqs/40741):
  the selected gun ends the mission with twice its starting ammo.
- [SuperCheats PSP tip](https://www.supercheats.com/psp/grand-theft-auto-liberty-city-stories/686/lots-of-bullets/):
  "I got 5000-9969 for the sub machine gun when I played two times".

On PS2 the doubling stops at 9999. PS2 `CPed::GiveWeapon` (`SLES_541.35`
`0x1e1180`) clamps the new total to 9999 whenever it lands in 10000..29999:

- same weapon type: add the ammo, cap at 99999 (or the per-weapon max), then
  `if (total - 10000 < 20000) total = 9999`.
- different type in a mergeable slot (4-6: shotgun, SMG, rifle): merge the old
  ammo into the new amount and apply the same clamp.

Totals of 30000 and up pass through. That range is the game's "infinite"
amount: `CPed::AttachPedToEntity` (`0x1f08d0`) and rampages hand out 30000.
The HUD (`CHud::Draw`, `stories/src/renderer/Hud.cpp:616`) hides the count
once the reserve reaches 9999, so the clamp keeps every finite total visible.
9999 total minus a 30-round clip is exactly the 9969 the PSP player saw.

## Root cause in reLCS

`CPed::GiveWeapon` (`stories/src/peds/Ped.cpp:4660`) is Vice City's. It caps
at 99999 and has no 10000..29999 clamp. Each Scooter Shooter attempt still
doubles the SMG, so after about six attempts from 200 rounds the total passes
10000. The HUD then hides the count, and the player has up to 99999 rounds
with no visible counter: "infinite SMG ammo".

The attach/detach code (`AttachPedToEntity`/`DettachPedFromEntity`,
`Ped.cpp:9813-9880`) differs from PS2 in detail. PS2 replaces the attach
slot with `CWeapon::Initialise` and saves/restores that slot's previous
weapon. reLCS adds through `GiveWeapon` and restores only the selected
weapon. Either way the mission leaves the saved weapon in place before step
4, so both versions double. The doubling only happens when the SMG is
selected at the start, which matches the PS2 reports.

## Change

Port the PS2 clamp into `CPed::GiveWeapon`, stories only, through a small
`ClampFiniteAmmo` helper next to it in `Ped.cpp`:

- same-type branch: after the existing 99999 / max-ammo cap, set the total to
  9999 if it is in 10000..29999.
- different-type branch: when the slot is mergeable and the old ammo is added,
  apply the same clamp to the merged amount.

A fresh weapon in an empty slot keeps the amount it was given, like PS2.

The Scooter Shooter doubling stays, capped at 9999 like PS2.

## Rulings

- Ruling: keep the per-attempt doubling and only add the PS2 clamp. The
  doubling is documented original behaviour, and the clamp is what keeps it
  finite on PS2. Cost if wrong: a player can still raise SMG ammo to 9999 by
  replaying the mission, as on PS2.
- Ruling: do not port PS2's `AttachPedToEntity`/`DettachPedFromEntity`
  slot save/restore. The current code already produces the documented PS2
  outcome for this mission, and a port would add two `CPed` fields, which
  breaks 3DS saves (AGENTS.md landmine 17). Cost if wrong: other scripted
  attachments may restore a weapon differently from PS2. No report says so.
- Ruling: change stories only. III and miami keep their own `GiveWeapon`
  (their PS2/PC originals have no such clamp checked here). The commit message
  says so. Cost if wrong: none for the 3DS LCS build.
- Ruling: do not touch existing saves that already hold more than 9999 SMG
  ammo. The next `GiveWeapon` on that weapon clamps it back to 9999. Cost if
  wrong: a player keeps the large total until the next ammo pickup for that
  weapon.
- Ruling: leave `CPed::SetAmmo`/`GrantAmmo` (`Ped.cpp:4733-4770`) alone. The
  report goes through `GiveWeapon`, and their PS2 counterparts were not
  checked. Cost if wrong: another script path could still push a total past
  9999.

## Test

A host-compiled test (`scripts/tests/test_give_weapon_ammo_cap.py` with
`scripts/tests/cpp/give_weapon_ammo_cap.cpp`) extracts the real
`CPed::GiveWeapon` and checks:

- same type, total lands in 10000..29999: clamped to 9999.
- same type, total 30000 or more: kept.
- mergeable slot, different type, merged total in range: clamped to 9999.
- non-mergeable slot, different type: the old ammo is dropped, no clamp.
- empty slot, 30000 given: kept.
- the TP2 sequence from 200 rounds repeated eight times stops at 9999.
