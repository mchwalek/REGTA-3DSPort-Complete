# Stats screen: drop the rows left over from Vice City

Trello: "Stats being retained from reVC" (https://trello.com/c/zCNxlxOE).

## Intent

The reLCS pause-menu stats page still lists Vice City stats such as "Stores
knocked off" and "Assassination contracts completed". `CStats::ConstructStatLine`
(`stories/src/core/Stats.cpp`) is reVC's code and nobody ever checked it
against the LCS list. The page should show the rows that PS2 LCS shows, in
the same order.

## Ground truth

PS2 `CMenuManager::PrintStats` (`SLES_541.35` `0x33d2b0`) calls
`CStats::ConstructStatLine` at `0x231d50`. That function's row list, decoded
with Ghidra through REA, in order (rows marked "if > 0" are only listed when
the value is above zero):

1. `PER_COM`, `NMISON`, `ST_TIME`, `ST_OVTI`, `DAYSPS`, `NUMSHV`
2. `FEST_RP` (always shown, not gated on `nastyGame`), `PERPIC`
3. `PE_WAST`, `PE_WSOT` (only with `nastyGame`)
4. `CAR_EXP`, `BOA_EXP`, `HEL_DST`, `TYREPOP`, `ST_STAR`, `ST_STGN`, `TM_BUST`,
   `TM_DED`, `ST_HEAD`, `DAYPLC`
5. `ST_GANG` over ped types 7..15, that is `PEDTYPE_GANG1`..`PEDTYPE_GANG9`
   (`ST_GNG1`..`ST_GNG9`). reLCS stops before `GANG9`.
6. `GNG_WST`, `DED_CRI`, `HTMKLD` (if > 0), `KGS_EXP`, `BUL_FIR`, `BUL_HIT`,
   `ACCURA`, `CAR_CRU`
7. Distances: foot, car, bike, boat, then the total of those four. There is no
   golf-cart, heli or plane row.
8. `MXCARDM`, `MXCARJM` (always in metres), `MXFLIP`, `MXJUMP`, `BSTSTU` + stunt
   name, `NOUNIF`
9. `ST_WHEE`, `ST_WHED`, `ST_STOP`, `ST_STOD`, `ST_FAPD`, `ST_2WHE`, `ST_2WHD`
10. `ST_LOAN`, then `FEST_CC`, `FEST_HV`, `PASDRO`, `MONTAX`, `FEST_LS`,
    `FEST_HA`, `FEST_FE`, `FIRELVL`, each one if > 0
11. LCS odd jobs: car/bike sales, Love Media cars, Slash TV, trash, Avenging
    Angels (+ per-district levels), Wong Side of the Tracks, heli race,
    outfit changes, RC races, BSRPS races, Bump & Grind, Go Go Faggio
12. `ST_MOVI`, `ST_PHOT`, `ST_PIZZ`, `ST_NOOD`, `MO_TOUR`, `TA_TOUR`, `ST_GARB`,
    `ST_ICEC` (each if > 0)
13. The `HighestScores`/`FastestTimes` block, in the same order as reLCS now
14. `SC_SCRA`, `SC_9MM`, `SC_SCOO`, `SC_WICH` (if > 0), `FEST_CN`, `FEST_TR`
    (`nastyGame` only)
15. `ST_BRK`, `ST_LTBR` (if > 0), `ST_DRWN`, `SEAGULL` (if > 0)
16. Favourite/least favourite radio (`FEA_FM0`..`FEA_FM8`, default `FEA_FM9`).
    PS2 ranks only the ten stations 0..9 (`0x230528`, `0x2305b0`, `0x230600`).
    reLCS also looked at index 10, which is not a station.
17. `SPRAYIN`, `ST_WEAP`, `ST_AUTO`, `ST_DAMA`. `ST_DAMA` reads the
    `PropertyDestroyed` int (`0x3d9e90`, raised by the vehicle/ped damage code).
    reLCS and reVC pass `PropertyBudget` there instead.
18. `PROPOWN` + owned properties (if > 0), `CHASE` + media string, `OUTFITS` +
    unlocked costumes

PS2 doesn't list these reLCS rows: `ST_STOR` (stores knocked off), `ST_ASSI`
(assassinations), `ST_FTIM` + `ST_PRAN` (flight hours, pilot rank), `ST_FASH`,
`ST_PROP`, `DISTGOL`, `DISTHEL`, the feet-based `MXCARD`/`MXCARJ`, and the
plane term in the total distance.

## Goals

- Remove every row that PS2 doesn't list.
- Put the remaining rows in PS2 order, with PS2's "if > 0" and `nastyGame`
  conditions.
- Count `GANG9` (Sindaccos) for "Least favourite gang".
- Show `PropertyDestroyed` on "Property destroyed".
- Phase 2: record the LCS-only stats and list their rows too, so the page
  shows the full PS2 list.
- Phase 2: keep loading 3DS saves written before the new stats existed.

## Phase 2: the LCS-only stats

### Storage and writers

Each stat is a new `static` member of `CStats`, the same as the existing
ones. Most writers are script opcodes that reLCS parses and then ignores
(commented out in `Script9.cpp` and `Script10.cpp`). PS2 handles them in
the opcode switches at `0x2f0e70` and `0x273140`:

| Opcode | PS2 global | Update | Row |
|---|---|---|---|
| `REGISTER_CAR_SOLD` / `ADD_MONEY_MADE_WITH_CAR_SALES` | `0x3da13c` / `0x3da140` | `++` / `+=` | `CARSLD`, `MONCAR` |
| `REGISTER_BIKE_SOLD` / `ADD_MONEY_MADE_WITH_BIKE_SALES` | `0x3da144` / `0x3da148` | `++` / `+=` | `BIKESLD`, `MONBIKE` |
| `REGISTER_PACKAGE_SMUGGLED`, `REGISTER_SMUGGLER_WASTED` | `0x3da160`, `0x3da164` | `++` | none |
| `REGISTER_FASTEST_SMUGGLING_TIME` | `0x3da168` | min, 0 = unset | none |
| `ADD_MONEY_MADE_IN_COACH` | `0x3da16c` | `+=` | none |
| `ADD_MONEY_MADE_COLLECTING_TRASH` | `0x3da170` | `+=` | `MONTRS` |
| `REGISTER_HITMAN_KILLED` | `0x3da174` | `++` | `HTMKLD` |
| `REGISTER_GUARDIAN_ANGEL_MISSION_PASSED` | `0x3da17c` | `++` | `GDAMSP` |
| `REGISTER_HIGHEST_GUARDIAN_ANGEL_JUSTICE_DISHED` | `0x3da178` | `++`, the parameter is ignored (`0x231c88`) | `HGAJD` |
| `REGISTER_GUARDIAN_ANGEL_LEVEL` (3 params) | `0x3da180..188` | max per district | `IND_ZON`, `COM_ZON`, `SUB_ZON` |
| `REGISTER_BEST_BANDIT_LAP_TIME` / `_POSITION` | `0x668b80[i]` / `0x668b90[i]` | min, 0 = unset / min | RC races |
| `REGISTER_MOST_TIME_LEFT_TRAIN_RACE` | `0x3da18c` | max, 0 = unset (`0x231ca0`) | `FSTTRT` |
| `REGISTER_HIGHEST_TRAIN_CASH_EARNED` | `0x3da194` | max | none |
| `REGISTER_FASTEST_HELI_RACE_TIME` | `0x3da19c` | min, 0 = unset | none |
| `REGISTER_BEST_HELI_RACE_POSITION` | `0x3da134` | min | `BHLPOS` |
| `REGISTER_OUTFIT_CHANGE` | `0x3da1a0` | `++` | `TMSOUT` |
| `REGISTER_STREET_RACE_FASTEST_TIME` / `_LAP` / `_BEST_POSITION` | `0x668bd0[i]` / `0x668bb8[i]` / `0x668ba0[i]` | min, 0 = unset / same / min | street races |
| `REGISTER_FACE_PLANT_DISTANCE` | `0x3da100` (float) | max | `ST_FAPD` |
| `REGISTER_MAX_SECONDS_ON_CARNAGE_LEFT` | `0x3da0b0` | max | `FEST_CN` |
| `REGISTER_MAX_KILLS_ON_RC_TRIAD` | `0x3da0b4` | max | `FEST_TR` |
| `REGISTER_HIGHEST_LEVEL_SLASH_TV` / `ADD_MONEY_MADE_WITH_SLASH_TV` / `ADD_TOTAL_KILLS_ON_SLASH_TV` | `0x3da154` / `158` / `15c` | max / `+=` / `+=` | `SLTVLVL`, `SLTVMON`, `SLTVKIL` |
| `ADD_NOODLES_DELIVERED` | `0x3da0d4` (float) | `+=` | `ST_NOOD` |
| `REGISTER_SCRAPYARD_CHALLENGE_SCORE`, `_9MM_MAYHEM_`, `_SCOOTER_SHOOTER_`, `_WICHITA_WIPEOUT_` | `0x3da0f0..0fc` (float) | max | `SC_SCRA`, `SC_9MM`, `SC_SCOO`, `SC_WICH` |
| `ADD_MONEY_MADE_FROM_TOURIST` / `ADD_TOURISTS_TAKEN_TO_SPOTS` | `0x3da0d8` / `0dc` (float) | `+=` | `MO_TOUR`, `TA_TOUR` |
| `ADD_EXPORTED_CARS` / `SET_TOTAL_EXPORT_CARS` | `0x3da14c` / `150` | `+=` / `=` | `CARSEXP` (n of total) |
| `REGISTER_DIRT_BIKE_FASTEST_LAP` / `_TIME` | `0x668be8[i]` / `0x668c10[i]` | min, 0 = unset | Bump & Grind |
| `REGISTER_DIRT_BIKE_AIR_TIME` | `0x3da198` | max | `DBIKEAI` |
| `ADD_UNLOCKED_COSTUME` | `0x3da12c` (16 bits) | set bit, if bit < 16 | `OUTFITS` |
| `REGISTER_BEST_TIME_GOGO_FAGGIO` | `0x3da190` (ms) | min, 0 = unset | `FEST_GO` |
| crusher, `CGarage` crush (`0x197818`) | `0x3d9f84` | `++` | `CAR_CRU` |

"min, 0 = unset" is PS2's rule: store the value if the slot is 0, else keep
the smaller one. "max, 0 = unset" keeps the larger one in the same way. PS2 `CStats::Init` sets every new stat to 0, except the
bandit, street and heli race positions, which start at `INT_MAX` (no race
finished).

### Rows

The new rows go where PS2 puts them:

- `ST_OVTI` is row 3, after `ST_TIME`.
- `HTMKLD` (if > 0) after `DED_CRI`, `CAR_CRU` after `ACCURA`, `ST_FAPD`
  between `ST_STOD` and `ST_2WHE`.
- After `FIRELVL`: `CARSLD`, `MONCAR`, `BIKESLD`, `MONBIKE`, `CARSEXP`,
  `SLTVLVL`, `SLTVMON`, `SLTVKIL`, `MONTRS`, `GDAMSP`, `HGAJD` (each if > 0),
  the `GDA_HL` header with the three district levels, `FSTTRT`, `BHLPOS`,
  `TMSOUT` (always), the RC races (`BNDRACE` header, `BNDRAC0..2`, best
  position, fastest lap), the six street races (`BSRPS0..5`, position, lap,
  time), Bump & Grind (`DBIKEHE` header, `DBIKE0..9`, lap, time), `DBIKEAI`,
  `FEST_GO`.
- `ST_NOOD` after `ST_PIZZ`, then `MO_TOUR`, `TA_TOUR`.
- After `SHO_RAN`: the four scooter scores, then `FEST_CN` and `FEST_TR`
  with `nastyGame` only.
- After `CHASE`: the `OUTFITS` header and one `OUTF_00..15` row per
  unlocked costume.

PS2 `BuildStatLine` (`0x235448`) takes a seventh parameter, an indent n,
and puts n - 1 spaces in front of the label. Sub-rows use 2 or 4. reLCS
gets the same parameter, default 0.

Times on these rows are seconds shown as min:sec (PS2 helpers `0x237ca0`
and `0x237cd0`). `FEST_GO` stores milliseconds and shows ms / 1000.

### Playing time

PS2 keeps the total playing time before this session in `0x3d74dc`. Its
simple-vars save (`0x2f6168`) writes `0x3d74dc + CTimer` and its load
(`0x2f6418`) restores `0x3d74dc` but not `CTimer`, so after a load
`ST_TIME` ("Current playing time") counts from zero and `ST_OVTI` ("Total
playing time") is the sum. reLCS already restores `CTimer` from LCS7 saves,
so `CTimer` is the total. reLCS records the timer when the session starts
(`CStats::Init` and `CStats::LoadStats`). `ST_TIME` shows the timer minus
that value, and `ST_OVTI` shows the timer.

### Save format

On 3DS the stats block is a raw copy of the fields with no version. The
new fields go after the existing ones, at the end of `SaveStats` and
`LoadStats`. The block already carries its size, and `LoadStats` gets it.
`LoadStats` reads the new fields only if the block has room for all of
them. If not, the save is older and the new fields get the PS2 start
values from `CStats::InitLcsStats`, which `CStats::Init` also calls. The save magic stays LCS7. Older binaries never read past the old
fields and only check the size through an `assert`, which `MASTER` builds
compile out.

The new fields add about 330 bytes. The whole save has a fixed size
(`SIZE_OF_ONE_GAME_IN_BYTES`, padded at the end), so they come out of the
padding.

## Non-goals

- The stats page layout (`PrintStats`), which was already ported from PS2.
- III and miami. This change is stories only.

## Approaches

1. **Delete only the two rows named on the card.** This is the smallest diff,
   but it keeps the other VC rows (flight hours, pilot rank, fashion and
   property budgets, golf-cart distance) and the wrong `ST_DAMA` value.
2. **Make the list follow PS2 for the data that exists (chosen).** This is
   one function in one file. It doesn't change the save format, and the page
   then matches PS2 except for the missing LCS-only rows.
3. **Full PS2 parity, including the new LCS stats.** This is many files, a
   save-format change (the stats block is a raw blob on 3DS) and opcode work
   in the script VM. Phase 1 shipped approach 2 first. Phase 2 does this
   one on the same card, with old saves still loading.

## Rulings

- Ruling: keep rows that PS2's code still has even where the SD card's
  `AMERICAN.GXT` has no key for them (`ST_LOAN`, `ST_MOVI`, `ST_GARB`,
  `ST_ICEC`, `TOP_SHO`, `SHO_RAN`, `STHC_*`, `STFT_*`, `PROPOWN`, `STPR_*`).
  All of them are gated on a value that LCS seldom or never sets, so they
  behave as on PS2. Cost if wrong: an unlabelled row in a rare case.
- Ruling: keep the existing unit selection (`USE_MEASUREMENTS_IN_METERS`
  makes English use metres). This is a port-wide config choice, not a VC
  leftover. Cost if wrong: English distances show in metres instead of miles.
- Ruling: keep reLCS's `MORE_LANGUAGES` gate on `ST_HEAD` for Japanese. It
  has no effect on the 3DS languages.
- Ruling: also store the stats that PS2 records but never lists (smuggling,
  coach cash, train cash, heli race time), so every opcode does what PS2
  does. Cost if wrong: about 24 unused bytes per save.
- Ruling: the per-race setters ignore an index outside the array. PS2
  writes past it. Cost if wrong: none, `main.scm` only passes valid indexes.
- Ruling: no new save magic. The block size tells old and new stats blocks
  apart, and a magic bump would also change how the rest of the file loads.
  Cost if wrong: a later stats change has to compare sizes again, which
  the same check handles.
- Ruling: `ST_TIME` now shows the time since the save was loaded, as on PS2,
  not the whole game's time. `ST_OVTI` shows the whole game's time. Cost if
  wrong: one label change, easy to undo.

## Verification

- A host-compiled test (`scripts/tests/test_lcs_stats_lines.py`) takes the
  real `ConstructStatLine`, runs it with stub stats, and checks the row key
  sequence for an all-zero and an all-set stats state, the `GANG9` pick, and
  the `ST_DAMA` value. Phase 2 adds the new rows to the all-set case, a
  case where every race is finished, and a check of the indent per row.
- A second host-compiled test (`scripts/tests/test_lcs_stats_save.py`) runs
  the real `SaveStats`, `LoadStats` and `InitLcsStats` code. It checks that
  a save round-trips every new field, that the fields before the new ones
  keep the old 3DS layout, and that an old-size block loads with the PS2
  start values.
- `scripts/build.sh relcs` compiles.
