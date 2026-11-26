# Bringing the House Down: construction tunnel pieces missing on 3DS

Trello: https://trello.com/c/vmRQsqkE

## Symptom

In "Bringing the House Down" (main.scm `DONH5`) Toni drives a van down the
Porter tunnel ramp (`pta_tunl_2_cus2`) into the Fort Staunton subway, which is
still under construction, and plants three bombs at (408.9, -62.9),
(375.1, -244.7) and (268.8, -345.8), all at z about -7. On 3DS parts of that
construction site have no geometry and no collision, and the player can drive
out of the map.

## Root cause

`SyncLCSFortStauntonWorld` (`stories/src/control/Script9.cpp`) deletes every
building with model ids 3653..3660 while Fort Staunton is intact:

```cpp
RemoveBuildingsInModelRange(3653, 3660);
```

Those ids are the construction set, all placed in `commer.ipl`:
`Siu_Beam1/2/3` (94 instances), `Over_hang` (21), `Slab_00` (3),
`Ramp00` (2), `FS_Train` (2) and `Rubble3` (2). The two `Rubble3` pieces at
(205.1, -64.8) and (421.6, -64.7) close the two ends of the subway tube. With
them gone the tube is open at both ends.

The fort is still intact for the whole drive. main.scm writes the destroyed
flag (global 4512) only in helper 0xd83f case 7 (`SET_VAR_INT` at 0xdd8e and
0xe063). DONH5 calls it with `[7, 1]` at 0x135acb, inside the ending
cutscene that also blows up the fort (0x134cca..0x135bca).

## PS2 behaviour

- **Rendering.** The construction pieces are ordinary instances in
  `COMMER.LVZ` and `UNDERG.LVZ`, for example `Rubble3` as instances 1375 and
  1376, `Over_hang` as 1545 and 1351, `Slab_00` as 1530. None of them is in
  either level's swap table. PS2 draws them in both fort phases.
- **Entities.** All 124 instances are in the static building table in
  `GAME.BIN`, the same set as `commer.ipl`. PS2 never deletes them.
- **Collision.** Their collision is in the `fortstaunton` COL slot (PS2 chunk
  for ids 3600..3664, the same data as the SD `fortstaunton.col`). PS2
  `CColStore::DoScriptsWantThisIn` (`0x1140e0`) wants `fortstaunton` only
  while the destroyed flag is clear, the same rule as reLCS. While the fort is
  intact the slot is loaded and the pieces are solid.

So on PS2 the construction set is present and solid for the whole mission.

## Fix

Stop deleting ids 3653..3660 in the intact branch of
`SyncLCSFortStauntonWorld`. Keep removing the destroyed-phase models
(3685..3741), which PS2 hides through swap slot 12. Update the comment, which
called the construction set "detailed rubble" and blamed it, together with
the destroyed LODs, for night-time z-fighting. The pieces sit underground
(z -8 to 7), far below the fort's streets at about z 20, so this change
assumes the z-fighting came from the destroyed LODs, which stay removed.

The destroyed branch does not change. It already keeps 3653..3660 and loads
`fortdestroyed.col` in place of `fortstaunton.col`, so the pieces have no
collision after the fort is destroyed. PS2 shows the same result after a
save is loaded with the fort destroyed, because `LoadCollision` (`0x113a88`)
skips a slot the scripts do not want. It differs only in the session where
the destruction happens: PS2 never unloads a slot that was already loaded.
The mission warps Toni to street level right after the destruction, so the
card does not need this case fixed.

## Test

A host-compiled regression test extracts the real `SyncLCSFortStauntonWorld`
from `Script9.cpp`, stubs `RemoveBuildingsInModelRange`,
`LoadLCSFortCollision` and `CFileLoader::LoadScene`, and checks:

- Intact phase: no removed range overlaps 3653..3660, and 3685..3741 is still
  removed.
- Destroyed phase: 3600..3652 and 3661..3664 are removed, 3653..3660 is not,
  and `fortdestroyed.ipl` is loaded.

## Risk

The construction pieces now render while the fort is intact, as on PS2. That
adds draw cost under Fort Staunton, and it brings back whatever z-fighting
the original removal was meant to fix, if any of it came from these pieces.
Nobody has checked this on a console.
