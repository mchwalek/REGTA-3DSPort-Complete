---
name: relcs-3ds-minimap-rectangle
description: The reLCS 3DS bottom-screen radar is a 320x240 rectangle, not PS2's circle. Use it when a radar blip is hidden, dimmed or misplaced near a corner or the right edge. Use it when you change CRadar::LimitRadarPoint, the radar edge inset, the blip fade or the north marker. Use it when you port PS2 radar code that assumes a unit circle.
---

# reLCS 3DS minimap: rectangular edge (stories)

The bottom screen has the radar as the full 320x240 area. PS2's radar is
a circle. Any PS2 rule that says "1.0 is the edge" needs the rectangle
version here.

## What PS2 does

- `CRadar::LimitRadarPoint` (`SLES_541.35` `0x1188e0`) returns the distance
  `|p|`. If `|p|` is above 1, it scales the point onto the unit circle.
- `DrawCoordBlip` (`0x115df8`) uses that return value in two places. A
  short-range blip is hidden when the value is above 1.0. The alpha comes from
  `CalculateBlipAlpha` (`0x118970`): 255 up to 1.0, then a fade to 128 at 10.0.
- So "1.0" means "the edge of the radar". Inside is full alpha. Outside is
  clamped to the edge and dimmed.

## What reLCS does on the 3DS

- `LimitBottomRadarPoint3DS` (static, `stories/src/core/Radar.cpp`) computes
  `edge = max(x / bound_x, |y| / bound_y)`. It divides the point by `edge`
  when `edge` is above 1. It returns `edge`. `LimitRadarPoint` returns that
  value on the bottom screen, so short-range hiding and the alpha fade follow
  the rectangle.
- The bounds sit 10 px inside the screen edge. In radar space they are x from
  -11/12 to 19/12 and y from -11/12 to 11/12. The screen position is x = 120 +
  120 * x and y = 120 - 120 * y. The inset keeps a sprite with a half size of
  9 px on the screen.
- The north marker sits at `2.0f * m_radarRange`, not `M_SQRT2 *
  m_radarRange`. The old value is outside a unit circle, but it is inside the
  rectangle toward the right edge (1.414 is less than 19/12). The farthest
  corner is at about 1.83, so 2.0 is always outside and the clamp puts the
  marker on the edge in every direction.
- The pause-menu map returns before any clamp. The top-screen round radar code
  is not built on 3DS.

## Known artifact

Blips near the right edge can sit partly under the translucent status rail on
the right of the screen. This is a ruling, not a bug. The map is drawn there
too. To move blips out from under the rail, change the right bound from 19/12
to 11/12. That is a one-line change.

## Other trees

`miami/src/core/Radar.cpp` has the same circle test. It was not changed.
III has no bottom-screen radar code.

Test: `scripts/tests/test_3ds_bottom_radar_edge.py` with the harness
`scripts/tests/cpp/bottom_radar_edge.cpp`. See
`git log --grep="bottom radar's rectangle"`.
