# Global lighting parity (reLCS 3DS buildings)

Trello card "Global lighting" / knowledge todo "lighting/fog": on 3DS the
world (seen e.g. through Toni's safehouse window) is much darker than on
PS2, and the overall look differs.

## Finding

- PS2 GS texture modulate treats a vertex colour of 128 as 1.0, so PS2 world
  geometry can reach 2x the texture colour. The scorched-wreck work already
  confirmed the same scale in the PS2 lighting microcode (ambient uploaded
  at 2x, `SLES_541.35` `0x184e60`).
- LCS buildings don't use VC's "prelight + ambient" formula. Desktop reLCS
  (aap's "Leeds" world pipe, `stories/src/extras/custompipes_gl.cpp`
  `worldRenderCB` + `shaders/leedsBuilding.vert`/`scale.frag`, default
  `WORLDPIPE_PS2`) does:
  `clamp(prelight * Ambient + Ambient_Bl * 0.5) * texture * 255/128`
  (`Ambient` = TIMECYC column 1, `Ambient_Bl` = the "EMISSION" column that
  drives the world ambient light).
- `config.h` undefines `EXTENDED_PIPELINES` for `_3DS`, so 3DS buildings ran
  through the default librw pipe: `clamp(prelight + Ambient_Bl) * texture`.
  At 10:30 sunny `Ambient` is ~0.9, so PS2 buildings come out ~1.8x brighter
  than 3DS. That is the "much darker" world.
- The Leeds pipe was taken from aap's desktop reimplementation (known PS2
  RE work). The building pipe itself was not separately disassembled in
  `SLES_541.35` (PS2 does it in VU1 microcode); my call.

## Change

- 3DS vertex shaders (`default`, `ps2/defaultfog`, `lighting`) multiply
  the prelight by a new uniform `u_prelightScale` (1 by default, so III,
  miami and all non-building draws are unchanged).
- `EntityRenderStyle::leedsBuildingLighting` marks building draws. It is set
  only by stories code (`CameraOcclusion3DS::RenderScope` under
  `RESTORIES_3DS_BUILD`, and `LCSPS2BuildingRenderScope`). With it set,
  `flushCache` uploads `u_prelightScale = timecycle Ambient` and halves the
  ambient light (emission x 0.5), and `defaultRenderCB` sets TEV stage 0's
  RGB scale to 2x for textured meshes.
- `SetLightsWithTimeOfDayColour` passes `CTimeCycle::GetAmbient*()` to
  librw (`rw::c3d::setLeedsBuildingAmbient`).
- Applies whether or not the "PS2 graphics" option is on: it is base
  lighting, not the optional fog/colour grade (my call).

## Not covered (my calls)

- Only `CBuilding` entities. Objects keep their lit path (directional +
  `Ambient_Obj`), as on desktop.
- Env-mapped (matfx) buildings draw unlit on 3DS and are unchanged.
- Distant proxies while silhouette-blended get the vertex part but not the
  2x texture scale.
- 3DS keeps `surfAmbient` and material RGB in the formula; desktop ignores
  them. Both are normally 1 on buildings.
- Fog distances and the PS2-graphics colour grade (`PS2GraphicsProfile.h`,
  self-described as not measured) are untouched; revisit after testing
  this on hardware.
