# More readable text on the 3DS top screen (reLCS)

Trello: https://trello.com/c/V4FK1rnJ/60-more-readable-text

## Why

reLCS keeps PS2's text sizes (640x448 basis). On the 400x240 top screen
`SCREEN_SCALE_X` is x0.5 and `SCREEN_SCALE_Y` x0.536, so PS2-sized text is
about half size. Stats rows were ~6 px tall, map hints/zone name ~7 px.

## Goals (card order)

1. Stats menu rows, heading and rating.
2. Map screen: legend, zone (district) name, button hints.
3. Upper-left help box (e.g. "press R3 to start taxi mission").
4. Save/load messages in the centre of the screen.
5. Objective text at the bottom, only slightly.

Non-goals: other menus' layouts, HUD numbers, zone/vehicle names, bottom
screen. Non-`_3DS` builds stay unchanged (everything is `#ifdef _3DS`).

## Decisions (agent's calls; user opted out of questions)

- Per-site scale bumps, no global font scale (a global one would break
  every hand-placed layout).
- Stats: reLCS still drew Vice City's screen (black rows on a light
  polygon). `_3DS` now ports PS2 LCS's `0x33d2b0` in PSP 480-wide
  coordinates: white rows at scale 0.3834/0.71 (0.3451 non-American),
  15 apart, label x 21 / value x 460, fading between y 52-72 and 176-196;
  "CRIMRA" left and the light-blue (118,176,220) rating name + "(N)" right on
  y 40; no background polygon. That gives ~9.5 px text without enlarging.
- Map legend: box spans the full width from y 70, two columns at x -40/330
  (640 basis), entries 0.75/0.95; the row step shrinks (and the text with it)
  if a long legend wouldn't fit above y 440.
- Zone name: MEDIUMTEXT, moved up to clear the bigger helper row.
- `DisplayHelperText`: SMALLTEXT instead of SMALLESTTEXT for all menus.
- Help box: 0.62/1.3 (was 0.52/1.1), wrap 300 (was 230); the radar is on
  the bottom screen, so the extra width is free.
- Save/load box: 0.62/1.35, centre size 470, text centred in the box.
- Objective text: ~10% bigger (0.64/1.34); with `ENABLE_3DS_BOTTOM_RADAR`
  it centres on the full width instead of leaving room for the radar.

## Left to verify

Look on hardware: long German/French strings in stats and legend, and
multi-line save/load messages.
