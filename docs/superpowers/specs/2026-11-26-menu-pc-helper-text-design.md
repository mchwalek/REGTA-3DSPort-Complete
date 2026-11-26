# Drop PC mouse/keyboard helper text from the 3DS menus

Trello: [Some menu settings mentioning mouse wheel to adjust](https://trello.com/c/cQE756C3/80-some-menu-settings-mentioning-mouse-wheel-to-adjust)

## Problem

On the Audio, Display, Graphics and Stats pages, reLCS prints a line in the
bottom-right corner. It comes from `CMenuManager::DisplayHelperText(nil)`
(`stories/src/core/Frontend.cpp`), which is reVC PC code:

| GXT key | Text in the SD card's `AMERICAN.GXT` | Shown for |
|---|---|---|
| `FET_MIG` | `LEFT, RIGHT, MOUSEWHEEL TO ADJUST` | almost every row of those pages |
| `FEH_SSA` | `CURSORS TO MOVE - S TO SAVE TO FILE` | the Stats page |

A 3DS has no mouse wheel, no cursor keys and no `S` key. The card asks
whether to drop only the mouse-wheel part or the whole line.

## What PS2 does

- The PS2 disc's `/TEXT/ENGLISH.GXT` has neither `FET_MIG` nor `FEH_SSA`, and
  no other `FET_*` or `FEH_*` helper strings (`FEH_NA`, `FET_APP`, `FET_HRD`,
  `FET_RSO`, `FET_STS` and `FET_RSC` are also missing). The SD card's GXT has
  them because it is a PC-style file.
- PS2 draws a row of button icons with short labels instead. The labels are
  `FEI_SEL` Select, `FEI_BAC` Back, `FEI_NAV` Move, `FEI_ZOO` Zoom,
  `FEI_SCR` Scroll, `FEI_RES` Resume, `FEI_LE1/2` Legend, `FEI_TA1/2`
  Target, `FEI_CHA` Change Team. The row builder is `SLES_541.35`
  `0x345dd8`, which picks items by page (`+0x588`). The item drawer is
  `0x345ba0`, an 11-case switch over `0x343b80`..`0x344de0`. None of the
  items says how to change a setting's value.

So PS2 never shows an "adjust" hint, and the 3DS text is not a PS2 string.

## Approaches

1. **Hide `FET_MIG` and `FEH_SSA` on 3DS (chosen).** This matches PS2, which
   has no such text. It is a small change and keeps the other helper lines.
2. **Replace them with 3DS text**, for example `LEFT, RIGHT TO ADJUST`
   through `GetPlatformFrontendText`. This keeps a hint, but it adds a string
   that neither PS2 nor the SD GXT has, and the slider rows already show the
   value next to the label.
3. **Port the PS2 button-icon row.** This is the faithful fix, but it needs
   new icon art and per-page layout on the smaller 400x240 screen. The 3DS
   menus differ from PS2's anyway (as the card notes), so the cost does not
   pay off for this card.

## Design

- Move the key choice of the default case in `DisplayHelperText` into a new
  file-static function in `Frontend.cpp`:

  ```cpp
  static const char *GetDefaultHelperTextKey(int32 action, int32 screen,
                                             bool noAudioProvider, bool gameNotLoaded);
  ```

  It returns the GXT key to print, or `nil` for no text. Off `_3DS` it returns
  exactly what the old code printed. On `_3DS` it returns `nil` where the old
  code printed `FET_MIG` or `FEH_SSA`.
- `DisplayHelperText` prints `TheText.Get(key)` when the key is not `nil`,
  and prints nothing otherwise.
- `FEH_NA` (`OPTION NOT AVAILABLE`) still shows on 3DS. It says something
  true about the row and names no PC input.
- The timed status messages (`m_nHelperTextMsgId` 1-5) are unchanged.
- Only `stories/` changes. III and miami keep their PC text.

## Rulings

- Ruling: hide the whole line, not only the word "MOUSEWHEEL" — PS2's GXT has
  no adjust hint at all and its button row never explains how to change a
  value — cost if wrong: players lose a hint that left/right changes a value;
  easy to add back as 3DS text.
- Ruling: also hide `FEH_SSA` on the Stats page — it names cursor keys and an
  `S` key that a 3DS does not have — cost if wrong: none, the export it
  describes cannot be triggered on 3DS.
- Ruling: keep `FEH_NA` and the timed status messages — they name no PC input
  and give real feedback — cost if wrong: some PC-style text stays; it is a
  separate card.
- Ruling: do not port the PS2 button-icon row — it needs new art and layout
  for a menu that already differs from PS2 — cost if wrong: a later card can
  still add it; this change does not block it.
- Ruling: touch `stories/` only — III and miami are separate trees with their
  own menus and no card asks for them — cost if wrong: the same text stays in
  those games.

## Tests

`scripts/tests/test_menu_helper_text.py` extracts `GetDefaultHelperTextKey`
and compiles it twice, with and without `-D_3DS`. It checks that the 3DS build
returns `nil` for every case that used to give `FET_MIG` or `FEH_SSA` and still
returns `FEH_NA`, and that the non-3DS build returns the old keys.
