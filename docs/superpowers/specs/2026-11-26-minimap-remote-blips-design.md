# Rectangular edge for remote blips on the 3DS bottom-screen radar

Trello: [Improve handling of remote blips on minimap](https://trello.com/c/KrjsBB8d/18-improve-handling-of-remote-blips-on-minimap)

## Why

The 3DS radar fills the whole 320x240 bottom screen, a rectangle. The code that
decides where a remote blip goes still treats the radar as PS2's unit circle.
`CRadar::LimitRadarPoint` (`stories/src/core/Radar.cpp`) does two things wrong
on the bottom screen:

1. It only treats a blip as off-radar when its radar-space distance is above
   1.0, the unit circle. A blip in a corner of the screen, such as (0.8, 0.8)
   at distance 1.13, is visible on the map. The code still moves it outward
   onto the rectangle edge, so the icon sits in the wrong place on the map.
2. It returns that circular distance. The callers use it to hide short-range
   blips (`dist <= 1.0`) and to fade blips (`CalculateBlipAlpha`). So a
   short-range blip in a corner, or in the strip right of x = 240, is hidden
   even though its map position is on screen, and visible blips there are
   drawn at half alpha.

## What PS2 does

PS2 LCS has a round radar. `LimitRadarPoint` (`SLES_541.35` `0x1188e0`) returns
`|p|`, and when `|p| > 1` it scales the point onto the unit circle. It returns
early on the pause-menu map. `DrawCoordBlip` (`0x115df8`) uses that return value
for the short-range test (`dist <= 1.0`) and for `CalculateBlipAlpha`
(`0x118970`: 255 up to 1.0, a fade to 128 by 10.0). So on PS2 "1.0" means "on
the radar's edge": inside is visible at full alpha, outside is clamped to the
edge, dimmed, and short-range blips are hidden. This port keeps that meaning
and only changes the shape of the edge.

## Goals

- On the bottom screen, a blip is off-radar only if it is outside the inset
  rectangle that the current code already uses as its edge.
- A blip inside that rectangle draws at its true position.
- An off-radar blip moves along the ray from the player to the rectangle edge
  (as now).
- `LimitRadarPoint` returns a rectangle measure: 1.0 on the inset edge, below
  1.0 inside, above 1.0 outside, and it scales linearly along a ray. Short-range
  blips and the alpha fade then work as on PS2, but for the rectangle.
- The north marker stays on the rectangle edge.

## Non-goals

- No change to the pause-menu map, which returns before any clamp.
- No change to the top-screen round radar code (not built with
  `ENABLE_3DS_BOTTOM_RADAR`).
- No change to blip sizes, sprites, colours, or the map tiles and clipping.
- No change to `miami/` or `III/`. `miami/src/core/Radar.cpp` has the same
  circle gate. III has no bottom-screen radar code.

## Approaches

1. **Rectangle measure in a helper (chosen).** Add a static
   `LimitBottomRadarPoint3DS(CVector2D &)` in `Radar.cpp`. It computes
   `edge = max(x / bound_x, |y| / bound_y)`, where `bound_x` is the left or
   right bound for the sign of x. If `edge > 1`, it divides the point by
   `edge`. It returns `edge`. `LimitRadarPoint` calls it on the bottom screen.
   This fixes the clamp, short-range hiding and alpha with one change, and the
   helper only uses `.x`/`.y`, so a host test can compile it unchanged.
2. **Fix only the clamp, keep the circular distance.** It is smaller, but
   short-range blips in the corners stay hidden and stay at half alpha. That is
   the same circle assumption the card reports.
3. **Clamp to the 240x240 square left of the status rail.** This keeps icons
   out from under the translucent status rail. It shrinks the map area that
   the port's own comment calls the radar's contract ("the complete 320x240
   display") and moves blips that are visible on the map today. Not chosen;
   see the rulings.

## Design

- Bounds, unchanged from the current code, in radar space (screen x =
  120 + 120 * x, screen y = 120 - 120 * y): left -11/12 (x = 10 px), right
  19/12 (x = 310 px), top and bottom ±11/12 (y = 10 and 230 px). The 10 px
  inset keeps a 9 px-half-size sprite fully on screen.
- `LimitBottomRadarPoint3DS` returns `edge` as above. The point (0, 0) gives 0.
- `LimitRadarPoint` keeps its menu-map early return, then on the bottom screen
  returns the helper's value.
- North marker: `DrawBlips` places it at `M_SQRT2 * m_radarRange` north of the
  player. That distance is always outside the unit circle, but it is inside the
  rectangle toward the right edge (1.414 < 19/12). On the bottom screen, put it
  at `2.0f * m_radarRange`. The farthest inset corner is at
  sqrt((19/12)^2 + (11/12)^2) ≈ 1.83, so 2.0 is always outside, and the clamp
  puts it on the edge in every direction.

## Rulings

- Ruling: keep the current inset rectangle (x 10..310, y 10..230) as the radar
  edge, including the strip under the status rail. Why: the map is drawn there
  and the existing code and comments name the full 320x240 display as the
  radar. Cost if wrong: blips near the right edge stay partly under the rail
  and its HUD text. A follow-up can move the right bound to 11/12 with a
  one-line change.
- Ruling: `LimitRadarPoint` returns the rectangle measure on the bottom screen,
  not the Euclidean distance. Why: PS2 uses the return value as "1.0 = radar
  edge" for the short-range test and the alpha fade, so the measure has to
  follow the edge shape. Cost if wrong: far blips fade at a slightly different
  rate along the long axis. The fade stays 255 to 128 between 1 and 10 edge
  units.
- Ruling: north marker at `2.0f * m_radarRange` on the bottom screen only. Why:
  `M_SQRT2` was chosen for a unit circle and does not reach the right edge of
  the rectangle. Cost if wrong: none visible, because the clamp puts the marker
  on the edge.
- Ruling: change `stories/` only. Why: the card is on the lcs_3ds board and
  AGENTS.md says the trees are not kept in sync. `miami/` has the same bug.
  Cost if wrong: Vice City keeps the old behaviour until someone ports the fix.
- Ruling: PS2's extra alpha rule in `DrawCoordBlip` (alpha 255 when an angle
  from `0x2d51d0` is beyond ±170) is out of scope. Why: it does not depend on
  the radar's shape, and reLCS does not port it today. Cost if wrong: none for
  this card.

## Test

A host-compiled test (`scripts/tests/test_3ds_bottom_radar_edge.py`, harness
`scripts/tests/cpp/bottom_radar_edge.cpp`) extracts `LimitBottomRadarPoint3DS`
from `Radar.cpp` and checks:

- a corner point inside the rectangle but outside the unit circle, such as
  (0.85, 0.85), is unchanged and returns ≤ 1;
- a point under the rail, such as (1.5, 0), is unchanged and returns ≤ 1;
- far points in each of the four directions and on diagonals land on the
  matching edge, keep their direction, and return > 1;
- the return value is linear: twice the point gives twice the value;
- (0, 0) returns 0 and stays at (0, 0);
- a point `2.0` units away in any direction returns > 1 (the north-marker
  distance).
