# Adrenaline pill prompt names R, not R1 (reLCS 3DS)

Trello: https://trello.com/c/yKWPc9zM ("[On-motorcycle side missions] R1
stated as adrenaline pill button").

## Problem

At the start of the three passenger-on-a-bike side missions (`main.scm`
scripts `TP1`, `TP2`, `TS1`), the help box says:

> You have 3 adrenaline pills, Press R1 button to use one.

The 3DS has no R1 button. The pill is used with R.

## Findings

- The text is GXT key `TUP_AD` in the `MAIN` table. All five languages spell
  the button as a literal `R1`, not as a `~k~` token, so the 3DS token
  mapping (`Messages.cpp`, `ControllerConfig.cpp`) never sees it:
  - AMERICAN: `Press R1 button to use one.`
  - FRENCH: `Appuie sur la touche R1 pour en utiliser une.`
  - GERMAN: `Drücke die R1-Taste, um eine zu nehmen.`
  - ITALIAN: `premi il tasto R1 per usarne una.`
  - SPANISH: `Pulsa el botón R1 para usar una.`
- PS2 `main.scm` polls the button in each of the three scripts with
  `IS_BUTTON_PRESSED 0 6` (raw file offsets `0x79124`, `0x7a664`, `0x7c1fc`).
  Button 6 is `RightShoulder1` (`CRunningScript::GetPadState`,
  `stories/src/control/Script5.cpp`). `CPad::AffectFrom3DS` sets
  `RightShoulder1` from `KEY_R` (`stories/src/core/Pad.cpp`). The button
  already works. Only the text is wrong.
- No other mission or help text in the GXT names a PS2 shoulder button
  literally. The other literal hits are the `C0`-`C3` label tables (not used
  on 3DS) and `FEDS_SM`/`FEDS_SS`/`FEI_R1B`, which only the dead
  `Frontend_PS2.cpp` reads.

## Approaches

1. **Rewrite the loaded string for `TUP_AD` in `CText::Get` (chosen).** A
   small `_3DS` table maps a key to a literal button name and its 3DS
   replacement (`TUP_AD`: `R1` -> `R`). `Get` copies the found string into a
   static buffer with the replacement applied. This works for every language,
   because each one contains `R1` as a separate token.
2. Hardcode a new English string for `TUP_AD`, like the `F3PS2` labels in
   `Text.cpp`. Simpler, but French, German, Italian and Spanish players would
   get English text.
3. Replace every standalone `R1`/`L1` in every string at load time. That
   reaches strings that do not need it (`FEDS_*`, the `C0`-`C3` tables) and
   is harder to reason about. Rejected.

## Design

- In `stories/src/text/Text.cpp`, add a `_3DS`-only helper that takes the GXT
  key and the found string. If the key is in its table, it copies the string
  into a per-entry static buffer and replaces the first standalone `R1` (not
  next to a letter or a digit) with `R`. The German `R1-Taste` counts as
  standalone because `-` is neither. Other keys come back unchanged.
- `CText::Get` calls it only when the key was found.
- The helper is idempotent and does not change the loaded GXT data, so a
  language switch or a reload needs no extra handling.
- Rewritten text: `Press R button to use one.`, `la touche R pour`,
  `die R-Taste`, `il tasto R per`, `el botón R para`.

Ruling: replace the literal in the loaded string instead of shipping new
translations. Why: it keeps the PS2 wording in every language. Cost if wrong:
one table entry in `Text.cpp`.

Ruling: say `R`, the label the port already uses for `RightShoulder1`
elsewhere (`Nintendo3DSButtons`, `FREE1` = `L`). Cost if wrong: one string.

## Scope

Stories only. III and miami do not have this mission text. No change to
input handling.

## Test

A host-compiled test (`scripts/tests/test_3ds_literal_button_text.py`)
extracts the helper from `Text.cpp` and checks the five real `TUP_AD`
strings, an unrelated key, a string with no `R1`, and that `R10`/`AR1` are
left alone.
