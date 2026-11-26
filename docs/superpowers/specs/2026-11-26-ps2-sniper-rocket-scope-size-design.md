# PS2-sized sniper and rocket launcher scope on 3DS

Trello: "sniper/rocket launcher scope" (lcs_3ds board, In progress).
Report: "The scope seems to take only a tiny portion of the screen."

Stories (`stories/`) only. III and miami are not changed.

## What is wrong today

Reference captures are in `$WORKSPACE_ROOT/scopes/` (`ps2_*.png`, `3ds_*.bmp`).

- **Sniper rifle and laser scope.** On PS2 the scope circle fills the full
  screen height. The sides outside it are black. On 3DS the circle is about
  136 px across on a 400x240 screen, inside a black frame.
- **Rocket launcher.** On PS2 the whole scene shows, with four small green
  brackets in the centre. On 3DS the brackets are the right size, but a black
  frame hides most of the scene (only about x 95..305, y 30..205 is visible).

Two pieces of port code cause this:

1. `CHud::Draw` (`stories/src/renderer/Hud.cpp`) draws the four `sitesniper`
   / `sitelaser` quadrants with a half-extent of `SCREEN_SCALE_X/Y(210)`.
   That is VC's PC value in the 640x480 basis. On the 3DS top screen it is
   105 px.
2. `Render2dStuff` (`stories/src/core/main.cpp:1808-1823`) draws VC's black
   borders around the sniper (`SCREEN_SCALE(210)`) and the rocket launcher
   (`SCREEN_SCALE(180/170/210)`). That is where the rocket launcher's black
   frame comes from. Even with a bigger sniper sprite, these borders would
   paint over it.

## What PS2 does (SLES_541.35, EUR)

Read with REA/Ghidra and `elf_tools.py`.

- **HUD coordinate space.** The HUD draw function `0x23f540` (`CHud::Draw`,
  sole caller `0x1f6440`, the `Render2dStuff` equivalent) lays sprites out in
  PSP 480x272 units. `FUN_00320d28` sets the only two scale globals,
  `0x3d89c0 = 4/3` and `0x3d89c4 = 512/272`. No other code stores to them.
  The sprite and rect drawers (`0x321560`, `0x321238`) multiply by them, so
  480x272 units cover the full 640x512 PAL frame.
- **Sniper / laser / camera branch** (camera mode not 0x22, 0x2a, 0x2d, 0x29,
  8 or 0x28). The centre is (240, 136). Four quadrants use UVs 0.01/0.99,
  like reLCS. Weapon 28 (sniper) uses sprite 0x3f `sitesniper` and weapon 29
  (laser) uses sprite 0x41 `sitelaser`. Both have these half-extents:
  - half-height 210 units,
  - half-width 280 units, or 210 when the widescreen flag `0x3d8daa` is set
    (`gp+0x1cba`, the same flag reLCS maps to `m_PrefsUseWideScreen` in the
    weapon-icon code).

  210/272 of the frame height is 0.772 H. In both modes the quadrants are a
  square of about 0.775 H half-extent on the display (4:3: 280 x (4/3)/480 =
  0.778 H). The sprite runs past the top and bottom of the screen.
- **Black side bars.** For non-camera weapons only, PS2 draws two opaque
  black rects in the same units: (-1, 0)-(30, 272) and (450, 0)-(480, 272).
  x 30 and x 450 are the widescreen quadrant edges (240 ± 210). The bars
  black out whatever the sprite does not cover. PS2 draws no top or bottom
  bars.
- **Camera viewfinder** (weapon 36): half-extent 238 x 120.6 (134 in
  widescreen), sprite 0x43 `viewfinder_128`, no bars.
- **Rocket launcher** (mode 8 or 0x28): one `siterocket` XLU sprite at raster
  (320, 256), half-size 40 (30 in widescreen), with a pulsing green colour.
  No black bars or frame of any kind.
- **The `Render2dStuff` borders.** `0x1f6440` still has VC's border block. It
  runs for weapons 28/29 (rects (0,0)-(480,-74) and (0,346)-(480,272)) and
  weapon 16 ((0,0)-(480,-44), (0,306)-(480,272)), with cam mode 7/39/8/40/46.
  The first rect of each pair has a negative height. The second starts below
  y 272. With the PSP-to-raster scale, both draw nothing on screen. So on PS2
  this block is dead, and the rocket launcher (weapon 30) is not even in its
  weapon list.

## Design

All changes are `#ifdef _3DS`. Non-`_3DS` code paths keep their behaviour.

1. **Scope rect helper.** Add a static helper in `Hud.cpp`:

   ```cpp
   static CRect GetPS2ScopeRect3DS(float halfWidthPSP, float halfHeightPSP);
   ```

   It maps PS2 PSP-unit half-extents onto the 3DS top screen around the
   screen centre. Both axes use one scale, `SCREEN_HEIGHT / 272`.
2. **Sniper and laser quadrants** use
   `GetPS2ScopeRect3DS(210.0f, 210.0f)`. On 400x240 that is a half-extent of
   185.3 px, so the rect is x 14.7..385.3 and y -65.3..305.3.
3. **Black side bars.** After the quadrants, for sniper and laser only, draw
   opaque black rects from x 0 to the scope's left edge and from its right
   edge to `SCREEN_WIDTH`, full screen height. This follows PS2's
   (-1..30, 450..480) bars, which cover exactly the space outside the
   quadrants.
4. **`Render2dStuff`.** Do not draw the VC border block on `_3DS`. PS2's
   version draws nothing, the sniper now draws its own bars in `CHud::Draw`,
   and the rocket launcher has no frame on PS2.
5. **Rocket launcher sight.** Leave `DrawSolidRocketSight` as it is. Its
   half-extent `SCREEN_SCALE(40)` gives 20 px, about 0.083 H. PS2 gives
   40/512 = 0.078 H vertically and (40/640) x (4/3) = 0.083 H horizontally,
   so it already matches.
6. **Camera viewfinder.** Leave it unchanged (see the rulings).

## Approaches considered

- **A. PS2 widescreen extents, scaled by screen height (chosen).** One
  uniform scale (`SCREEN_HEIGHT/272`) on a square-pixel screen keeps the
  circle round and reproduces PS2's 0.772 H. The 3DS top screen (5:3) is a
  wide, square-pixel frame, like PS2's 16:9 widescreen output.
- **B. PS2 4:3 extents (280 x 210) in a centred 4:3 sub-frame.** This gives
  186.7 x 185.3 px, almost the same as A. It needs a second, x-only scale for
  no visible gain.
- **C. `PSP_SCREEN_SCALE_X/Y` with the PS2 numbers.** Those macros scale both
  axes by `SCREEN_WIDTH/480` and measure y from the top of a 272-unit frame
  that is 226.7 px tall on 3DS. With 210 x 210 the circle comes out about 6%
  smaller than PS2 (175 px). With 280 x 210 it becomes an ellipse.
- **D. Enlarge only the `SCREEN_SCALE` constants.** This would be a tuned
  number with no PS2 source.

## Rulings

- Ruling: use PS2's widescreen half-extents (210 x 210 PSP units) with one
  `SCREEN_HEIGHT/272` scale. The 3DS top screen has square pixels and a wide
  aspect, like PS2 widescreen. The 4:3 numbers would give the same size
  within 1.5 px. Cost if wrong: the scope is about 1% off PS2 size. Easy to
  revert.
- Ruling: draw the black side bars from the scope rect's edges, not at
  PS2's literal x 30/450. Those literals are the widescreen quadrant edges,
  and that is what the bars are for. Cost if wrong: a few pixels of black at
  the extreme sides. Easy to revert.
- Ruling: skip `Render2dStuff`'s VC sniper/rocket borders on `_3DS`.
  Disassembly of PS2's `0x1f6440` shows this block draws nothing visible,
  and PS2 has no rocket launcher frame. Cost if wrong: none found. PS2
  screenshots show no frame.
- Ruling: keep the rocket launcher bracket size. It already matches PS2
  within 1 px. Only the frame was wrong.
- Ruling: leave the camera viewfinder (`WEAPONTYPE_CAMERA`) as it is. It is
  outside this card. Also, its PS2 4:3 and widescreen sizes differ (0.66 H vs
  0.88 H wide), so choosing between them is a separate decision. Cost if
  wrong: the viewfinder stays smaller than PS2, which it already is today.
- Ruling: keep the existing 3DS laser centre cross and laser dot code. Only
  the scope size and frame change.

## Non-goals

- Scope zoom/FOV, sniper zoom controls, and laser dot size.
- The camera viewfinder size.
- III and miami.

## Verification

- A host-compiled test (`scripts/tests/test_3ds_scope_size.py`) extracts
  `GetPS2ScopeRect3DS` and checks it on 400x240:
  - half-extent 185.3 px on both axes, centred;
  - the rect covers the full screen height;
  - it stays inside the screen width.

  The same test also checks that `Render2dStuff` compiles its VC border
  block out on `_3DS`.
- `scripts/build.sh relcs`, the Python suite, and `scripts/verify-layout.sh`.
- On-device check (by the user): sniper, laser scope and rocket launcher
  against the PS2 captures.
