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

## Non-goals

- LCS-only stats that reLCS doesn't store yet (`ST_OVTI`, `HTMKLD`, `CAR_CRU`,
  `ST_FAPD`, group 11, `ST_NOOD`/`MO_TOUR`/`TA_TOUR`, group 14, `OUTFITS`).
  Each one needs new `CStats` storage, a change to the save format and
  the script opcodes wired up (most are commented out in `Script9.cpp` and
  `Script10.cpp`). That is a separate follow-up.
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
   in the script VM. That is too large for this card.

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

## Verification

- A host-compiled test (`scripts/tests/test_lcs_stats_lines.py`) takes the
  real `ConstructStatLine`, runs it with stub stats, and checks the row key
  sequence for an all-zero and an all-set stats state, the `GANG9` pick, and
  the `ST_DAMA` value.
- `scripts/build.sh relcs` compiles.
