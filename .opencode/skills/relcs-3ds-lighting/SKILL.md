---
name: relcs-3ds-lighting
description: reLCS 3DS lighting for peds, vehicles and cutscene actors. Also the PS2 colour filter, fog, and the code that each PS2 Graphics switch gates. Use it to change entity lighting, ColourGain, FogStart, the silhouette effect or renderPS2Graphics. Use it when a 3DS scene is darker or brighter than PS2. Use it when the colour filter, fog or blur does not appear on the console.
---

# reLCS 3DS lighting, colour filter and fog

This skill covers the 3DS side. For PS2 disassembly of the same systems, use
the `ps2-lcs-decompilation` skill. AGENTS.md landmines #28, #35, #39 and #40
also apply.

## Entity lighting (peds, vehicles, cutscene actors)

- The 3DS skin path (`3dsskin.cpp`) and the MatFX paint path (`3dsmatfx.cpp`)
  have no per-vertex lighting. `getEntityMaterialColor`
  (`common/librw/src/3ds/3dsrender.cpp`) computes one colour for each atomic.
- The formula is in `common/3ds/PS2GraphicsProfile.h`:
  - `EntityLightChannel(ambient, dir) = min(1, 2*ambient + dir)`.
  - `dir` is the sum over the directionals of `colour * EntityLightFacing(v)`.
  - `EntityLightFacing(v) = 0.67 * ((1 + v) / 2)^2`, with
    `v = camera at · light at`.
  - The facing term is the mean brightness of a lit sphere: 0 from behind,
    about 0.17 from the side, 0.67 from the front.
- One value applies to the whole atomic. The brightness changes as the camera
  moves around a ped or a car. This is correct behaviour, not flicker.
- Light direction: the `at` vector of a light's LTM is the direction that the
  light travels. `CLights` (`stories/src/rw/Lights.cpp`) sets the sun's `at`
  to `-vecsun`. `v = +1` means that the light is
  behind the camera, so the subject is lit from the front.
- `World::enumerateLights` returns directionals only when the geometry has the
  `Geometry::NORMALS` flag. Ped and car DFFs on the SD card (`plr`, `cop`,
  `taxi`, `stinger`, `pcj600`) have normals, and the 3DS loader keeps the flag.
- Capacity: `MAX_ENTITY_DIRECTIONALS = 1 + 4`. The sun (`pDirect`) comes first,
  then the 4 `pExtraDirectionals` for lamps and headlights
  (`NUMEXTRADIRECTIONALS = 4`, `stories/src/core/config.h`). An inactive lamp
  does not have the `rpLIGHTLIGHTATOMICS` flag, so the enumeration skips it. More than 4
  lamps give a darker result than PS2.
- No game-side change is necessary: `CPed::SetupLighting`,
  `CVehicle::SetupLighting` and `CCutsceneObject::SetupLighting` already set
  the ambient and the directionals before the render.

## Gating: stories only, III and miami unchanged

- `CameraOcclusion3DS::RenderScope` (`common/3ds/CameraOcclusionRender.h`)
  sets the flags. The stories part is inside `#ifdef RESTORIES_3DS_BUILD`,
  and only `stories/build/GNUmakefile` defines that macro.
  - It sets `leedsBuildingLighting` for buildings.
  - It sets `leedsEntityLighting` for peds, vehicles and cutscene actors.
- A cutscene actor is a `CCutsceneObject`. `IsObject()` is true for it, and it
  draws through the skin path. Identify it with
  `entity->IsObject() && ((CObject*)entity)->ObjectCreatedBy == CUTSCENE_OBJECT`.
  Other objects do not get entity lighting.
- `EntityRenderStyle` initialisers are brace lists that are shorter than the
  struct, so a new `bool` field starts as `false`. `RenderScope` copies the
  previous style and then changes it. Each new flag must have a default of
  `false` and get its value only inside the stories guard.
- Car occupants render through their own `RenderScope` (`Entity.cpp:453`),
  so they get their own lighting flags.
- `scorched` has priority over `leedsEntityLighting` and keeps its old
  behaviour. `getAtomicAmbientLight` (MatFX) requests zero directionals.
- Tests lock the III and miami `ColourGain` output and the
  `leedsEntityLighting` default. Do not change them.

## Colour filter

- `ColourGain(game, channel, alpha)` branches on the `game` value. For LCS it
  returns `1 + colour`, the same as `colourfilterLCS.frag`
  (`dst += dst*blur`). The callers in `3dsdevice.cpp` pass `game`, so a new
  game branch needs no change at the call sites.
- `FogColourCompensation` returns `(1 + colour) / gain` for LCS. With the gain
  at `1 + colour` it is 1, so the fog colour does not change.

## Fog

- Timecycle fog start can be negative (cloudy, rainy, foggy and hurricane
  weather). Do not assume that it is 0 or more.
- `PS2Graphics3DS::FogStart` keeps fog start between 55% and 65% of the range
  when PS2 Fog is on. `Apply3DSFogProfile` (`stories/src/core/main.cpp`)
  calls it.
- Commit `6c8917f` reverted a near-fog change that let negative starts through.
  Fog was off on the test console, so nobody saw the change. At night in
  cloudy weather it added about 13% dark fog at the camera.
- `ps2SilhouetteWeight` (`3dsdevice.cpp`) turns distant world buildings into
  flat fog-coloured shapes. It measures from fog start and uses
  `PS2Graphics3DS::SilhouetteWeight`. An island LOD (`style.worldSkyline`)
  always gets weight 1.

## Where the code gates each PS2 Graphics part

`ps2Part(part)` in `3dsdevice.cpp` is `ps2Graphics && ps2GraphicsParts[part]`.
Outside librw, use `rw::c3d::ps2GraphicsPartEnabled(part)`.

| Part | Gated code |
|---|---|
| `PS2_PART_COLOUR_FILTER` | Gain quad in `renderPS2Graphics`. When it is off, the stock `RenderMotionBlur` runs (`main.cpp`). |
| `PS2_PART_BLUR` | History blend (30/255) and the 2-pixel echo in `renderPS2Graphics`. |
| `PS2_PART_FOG` | Fog setup in `3dsdevice.cpp`, `ps2SilhouetteWeight`, `FogStart`, `style.worldSkyline` (`Renderer.cpp`). |
| `PS2_PART_DRAW_DISTANCE` | Far clip x0.76, `ps2WorldRange`, `DetailRangeScale` 0.85 (`Renderer.cpp`, `VisibilityPlugins.cpp`), far driver fade (`CrowdDrawBudget.h`). |

The blur and filter code is in shared librw code. III and miami have no part
rows, so their four flags stay on.

## The colour filter or blur does not appear

`renderPS2Graphics` stops without a message in these cases:

1. The colour filter part and the blur part are both off.
2. The camera is not the top-screen camera.
3. The eye framebuffer is not 256x512 or not RGBA8/RGB8. The function skips
   that eye.
4. The eye texture does not exist yet, and free linear memory is less than
   2 MiB plus the buffer size (about 2.5 MB). `C3D_TexInit` can also fail.

Check the PS2 Graphics settings first (see the `ps2-lcs-decompilation`
skill, "check the PS2 Graphics settings before you compare screenshots").
