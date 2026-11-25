# Shoreside Vale northern tunnel: keep the glows, fade the mouth LOD by sector

Trello: [Strange opaque geometry in shoreside vale northern tunnel](https://trello.com/c/hmgOLkZ7).

This replaces parts of the two earlier specs:

- `2026-11-21-shoreside-tunnel-light-volumes-design.md` said PS2 has no
  `Trans_lights01-03` instances. It does. Only their mesh is missing.
- `2026-11-22-shoreside-tunnel-mouth-lod-design.md` hid `LODl_tunnel1`
  within 48.1 m of its centre. PS2 drops it much further east, at the
  tunnel bend, and fades it.

## Symptoms after the first two fixes

Compared on hardware and PCSX2 captures of the same drive (east to west and
back):

1. The tunnel has no orange glows and looks dark. The pre-fix 3DS build and
   PS2 both show a row of glows along the ceiling.
2. Driving west, the black `LODl_tunnel1` arch is in view from the bend
   (x -525) until about 48 m before the west mouth, then pops out in one
   frame. On PS2 it fades out at the bend over about half a second.

## What PS2 does

### The light instances

`GAME.DTZ` (decompressed) has a 2dfx table at `0x4e3360`-`0x4e3aa0` with 30
coronastar records, 0x40 bytes each, colour 249,145,34,200. They match the
SD `suburb.ide` entries for models 3116, 3117 and 3118 (8, 12 and 10
records). The compiled building records at `0x2b2720`, `0x2b2780` and
`0x2b27e0` hold the `suburb.ipl` positions and those model ids at +0x58. So
PS2 keeps the three instances and their glows. `SUBURB.LVZ` has no mesh for
these models, so PS2 never draws one.

`626e49f` skipped the instances at load time. That removed the slab, and the
glows with it: `CCoronas` gets them from `ProcessLightsForEntity`, which
runs from `PreRender` on entities in the visible and alpha lists.

### The LOD sector crossfade

`SUBURB.LVZ` lists `LODl_tunnel1` only in the sectors east of the bend. In
the world loop (`0x200fb0`), a sector change sets a counter (`+0x4c`) to
479. The counter drops by 32 per frame at 25 fps. While it is 255 or more,
content that only the new sector lists fades in with alpha
`min(255, 512 - counter)`. Below 255, content that only the old sector
lists fades out with alpha `counter`. The new content is fully in after 8
frames and the old content is gone after 15, about 0.6 s.

## Fix

Stories only, `_3DS` builds.

### Draw no mesh for `Trans_lights01-03`

- Revert the load-time skip in `CFileLoader::LoadObjectInstance`.
- `CRenderer::Init` resolves the three model ids by name.
- New `CRenderer::ShouldRenderEntityMesh3DS(CEntity *)` returns false for
  them and otherwise defers to `ShouldRenderAttachedWindowLights`. It
  replaces that call at the three 3DS draw sites: `RenderOneNonRoad`,
  `RenderOneBuilding` (`Renderer.cpp`) and `RenderFadingEntities`
  (`VisibilityPlugins.cpp`).
- The entities stay visible to the scan, so `PreRender` still adds their
  glows. `bIsVisible = false` or `VIS_INVISIBLE` would drop the glows too.

### Fade `LODl_tunnel1` at the bend

- `IsLCSTunnelLodListedAt(cam)` is false inside the bounds of the tunnel
  models `Section_02` (-719.6..-480.1, 567.5..651.2, 77.0..91.4) and
  `Section_03` (-907.1..-717.6, 587.8..650.9, 76.8..92.5) west of x -525,
  and true everywhere else.
- `UpdateLCSTunnelLodCrossfade(cam, timeStep)`, called from
  `CRenderer::ConstructRenderList` after the camera position is set, resets
  the counter to 479 when that result changes. Otherwise it lowers the
  counter by `16 * timeStep`: timestep 2.0 is one 25 fps frame, so the fade
  takes the same game time at any frame rate.
- `LCSTunnelLodCrossfadeOpacity` turns the counter into opacity with PS2's
  two phases. `LCSPS2BuildingOpacity` multiplies it into every return for
  `LODl_tunnel1`, also with PS2 draw distance off. At 0 the visibility
  setup returns `VIS_INVISIBLE`. Between 0 and 1, `drawInst` alpha-blends
  the mesh.
- The 48.1 m rule from the second spec stays. It still covers the camera
  outside both boxes next to the mouth.

## Not changed

- The general LOD handoff (see the second spec: 114 of 786 pairs have LOD
  geometry more than 10 m outside the detailed bounds).
- A sector crossfade for any other model. PS2 fades all sector changes; the
  3DS port has no sector lists. Only this LOD is a confirmed problem.
- The glow data. Positions and colours already match PS2.

## Testing

- `scripts/tests/test_tunnel_light_meshes.py`: the three ids and nothing
  else are meshless, an unresolved name matches no model, `CRenderer::Init`
  resolves the names, all three draw sites use the new gate, and the loader
  keeps the instances.
- `scripts/tests/test_tunnel_mouth_lod.py`: sector rule at points east and
  west of the bend, in the overlap of both boxes, west of the mouth, on the
  hill above and south of `Section_03`. Westbound at timestep 2.0 the LOD
  stays at full opacity for 8 frames, then fades out and is 0 at frame 16.
  Eastbound it fades in and is full from frame 8. A crossing back during a
  fade restarts it. At timestep 5/3 the fade-out takes 18 or 19 frames.
- `scripts/build.sh relcs`, the full Python suite, `scripts/verify-layout.sh`.
- On the console: drive through the tunnel both ways, day and night. The
  glows are back and no slab shows. Driving west, the arch fades out at
  the bend instead of popping near the mouth.

## Rulings

- Ruling: skip only the mesh draw for `Trans_lights01-03` — PS2 keeps the instances and their 30 glows, and `SUBURB.LVZ` has no mesh for them — cost if wrong: the slab or the glow loss comes back, easy to see on a drive.
- Ruling: model the PS2 sector boundary with the two tunnel section boxes and x -525 — the 3DS port has no sector lists, and the bend is where PS2 drops the LOD in the captures and in `SUBURB.LVZ` — cost if wrong: the arch shows or fades a few metres early or late.
- Ruling: scale the PS2 counter step by timestep — the 3DS runs near 30 fps, not 25 — cost if wrong: the fade is a few frames longer or shorter.
