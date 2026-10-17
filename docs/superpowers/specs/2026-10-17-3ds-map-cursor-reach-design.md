# 3DS Map Cursor Reach — Design

## Problem

On the 3DS map screen (`stories/src/core/Frontend.cpp`, `MAP_ENHANCEMENTS`
path, `_3DS` build), the crosshair used to place a waypoint is fixed at
screen centre and the map pans underneath it. The map's own pan clamp uses
the PC values `m_fMapSize - MENU_X(MAP_MIN_SIZE)` / `m_fMapSize -
MENU_Y(MAP_MIN_SIZE)`, which assumes the crosshair can reach the map edges
when the map is smaller than the screen. On 3DS the map atlas is drawn at
`320x220` aspect (`PrintMap`, `:6129`) with no "off map" screen margin the
way PC's windowed/PS2 layout has, so that clamp stops the centre crosshair
short of the map's true edges — some waypoint-eligible map points can never
be placed under the crosshair, at any zoom level.

Additionally, the horizontal-pan gate `m_fMapSize > MENU_X
(MAP_SIZE_TO_ALLOW_X_MOVE)` blocks sideways panning entirely at minimum
zoom, compounding the problem at the zoom level most likely to be used for
waypointing a wide area.

## Scope

- `stories/src/core/Frontend.cpp` only, inside `#ifdef _3DS` (new) and the
  existing `#ifdef MAP_ENHANCEMENTS` region (`AdditionalOptionInput`,
  `MENUPAGE_MAP` case, roughly lines 3825-3942).
- No change to non-`_3DS` builds (III, miami, and non-`_3DS` stories) — all
  existing PC-path macros/branches are preserved byte-for-byte.
- No change to the waypoint hit-test / screen-to-atlas math
  (`:3835-3849`), the map rendering (`PrintMap`), or starting map position
  (`:673`, `:740`) — these already use the correct 320x220 atlas geometry.

## Approach: overscroll panning

Keep the fixed-centre crosshair. On `_3DS`, widen the pan clamp to the
map's own half-extent in each axis (so the map can be panned until its
own edge reaches screen centre, at any zoom), and lift the
`MAP_SIZE_TO_ALLOW_X_MOVE` gate so horizontal panning works at minimum
zoom too. Panning past the clamp just shows the black backdrop already
drawn behind the map in `PrintMap` (`:6127`) — there is no new rendering
work.

### 1. Per-platform pan-limit macros

Next to the existing `MAP_MIN_SIZE` platform split (`:125-132`), add:

```cpp
#ifdef _3DS
// Fixed centre crosshair: let any map point pan under screen centre, in
// either axis, at any zoom — matches the 320x220 atlas half-extent used
// by PrintMap/DrawLCSMenuMap3DS.
#define MAP_PAN_LIMIT_X(s) ((s) * (320.0f / 220.0f))
#define MAP_PAN_LIMIT_Y(s) (s)
#else
#define MAP_PAN_LIMIT_X(s) ((s) - MENU_X(MAP_MIN_SIZE))
#define MAP_PAN_LIMIT_Y(s) ((s) - MENU_Y(MAP_MIN_SIZE))
#endif
```

`MAP_PAN_LIMIT_X`/`_Y` take `m_fMapSize` and return the clamp half-range
to use in `Clamp(m_fMapCenterX/Y, SCREEN_WIDTH|HEIGHT/2 - limit, limit +
SCREEN_WIDTH|HEIGHT/2)`. The PC branch reproduces today's expressions
exactly (no behavior change off `_3DS`).

### 2. Replace the five existing clamp call sites

All within the `MAP_ENHANCEMENTS` branch (compiled for every platform that
defines it, so this only ever changes behavior where the new `_3DS` macro
differs from the old expression):

- `ZOOM` macro clamp — `:3779-3780`
- mouse-drag clamp — `:3885-3886`
- D-pad/circle-pad edge checks — `:3900`, `:3909`, `:3918`, `:3937`

Each `m_fMapSize - MENU_X(MAP_MIN_SIZE)` becomes
`MAP_PAN_LIMIT_X(m_fMapSize)`, and each `m_fMapSize - MENU_Y(MAP_MIN_SIZE)`
becomes `MAP_PAN_LIMIT_Y(m_fMapSize)`.

The `#ifndef MAP_ENHANCEMENTS` block (PC fallback with no pan/zoom) is not
compiled on `_3DS` and is not touched.

### 3. Lift the minimum-zoom horizontal-pan gate on 3DS

At `:3918` and `:3937`, `m_fMapSize > MENU_X(MAP_SIZE_TO_ALLOW_X_MOVE)`
gates D-pad/circle-pad left/right panning. Wrap this condition so it is
unconditionally true under `_3DS`:

```cpp
#ifdef _3DS
#define CAN_PAN_X_AT_CURRENT_ZOOM true
#else
#define CAN_PAN_X_AT_CURRENT_ZOOM (m_fMapSize > MENU_X(MAP_SIZE_TO_ALLOW_X_MOVE))
#endif
```

used in place of the raw comparison at both sites. The PC mouse-wheel use
of the same constant at `:3868` is unrelated (gates diagonal-only zoom vs.
pan-then-zoom) and is left as-is.

## Behavior after the fix

- At any zoom level, any point on the Liberty City map atlas can be panned
  under the fixed centre crosshair and have a waypoint toggled on it via
  `CRadar::ToggleTargetMarker`.
- Panning past the map's true edge shows the existing black backdrop;
  nothing new is drawn.
- Zoom-toward-crosshair behavior (`ZOOM` macro) is unchanged other than
  using the wider clamp afterward.
- Pan speed (`MENU_Y(15.f)` per input tick) is unchanged.
- Non-`_3DS` builds (including non-`_3DS` stories, and III/miami which
  don't reach this code path at all) are byte-for-byte unaffected.

## Testing

- New host-compiled test `scripts/tests/test_3ds_map_pan.py`, following the
  existing pattern of extracting small `_3DS` fragments from `Frontend.cpp`
  and compiling/asserting with the host `c++` compiler (see
  `scripts/tests/test_3ds_world_and_menus.py` for the established
  approach). Asserts that at both `MENU_Y(MAP_MIN_SIZE)` (3DS min zoom,
  224) and `MENU_Y(1000.0f)` (max zoom), the clamped `m_fMapCenterX`/`Y`
  range lets the screen-centre crosshair reach all four atlas corners
  (`0,0` and `320,220` in atlas space) through the existing
  screen→atlas conversion math at `:3838-3842`. Fails against the current
  (pre-fix) clamp expressions.
- Run `python3 -m unittest discover -s scripts/tests -p 'test_*.py'` and
  `scripts/verify-layout.sh`.
- Build with `scripts/build.sh relcs`.
- On-console/emulator manual check: at minimum zoom, pan to each of the
  four map corners and confirm a waypoint can be placed and shows on the
  HUD radar; repeat at max zoom.
