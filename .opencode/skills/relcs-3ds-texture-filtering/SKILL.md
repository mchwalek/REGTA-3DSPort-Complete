---
name: relcs-3ds-texture-filtering
description: How texture filtering, mip levels and the SD texture cache work in the 3DS librw backend. Use it when a texture looks blocky or shimmers when scaled down. Use it when a TEXTUREFILTER render state seems to have no effect. Use it when you add mip levels to ETC1 textures or change radar tile or pause-menu map drawing.
---

# 3DS texture filtering and mip levels (shared librw, all three trees)

AGENTS.md landmines 35 and 49 give the rules in short form. This skill gives
the detail behind them. The code is in `common/librw/src/3ds/3dsdevice.cpp`
and `3dsraster.cpp`.

## Two ways to bind a texture

- `setTexture` (the material pipeline) calls `setRasterStage` and then
  `setRasterParams` with the texture's filter and addressing. The texture's
  own filter applies.
- `setRasterStage` alone (the `TEXTURERASTER` render state, used by
  `CSprite2d`) binds the raster and never calls `setRasterParams`. The raster
  keeps its own sampler.
- `rwRENDERSTATETEXTUREFILTER` calls `setRasterParams(0, ...)`. It changes
  only the raster that is bound to stage 0 at that moment. A filter set before
  you bind a new raster changes the previous raster.
- `allocateETC` creates every ETC raster with NEAREST. To filter one texture,
  call `rw::c3d::rasterSetFilterMode` on its raster. Do not set the render
  state in the draw code.

## Mip filter

`updateRasterParams` sets the PICA mip filter from `filterConvMap_MIP`
(`C3D_TexSetFilterMipmap`). The mapping follows the gl3 backend:

| RW filter | texel filter | mip filter |
|---|---|---|
| `NEAREST` | NEAREST | NEAREST |
| `LINEAR` | LINEAR | LINEAR |
| `MIPNEAREST` | NEAREST | NEAREST |
| `MIPLINEAR` | LINEAR | NEAREST |
| `LINEARMIPNEAREST` | NEAREST | LINEAR |
| `LINEARMIPLINEAR` | LINEAR | LINEAR |

The PICA GPU always selects a level when a texture has levels, so `LINEAR` on
a mipped texture is trilinear. The mip filter has no effect on a texture with
one level. No texture on the SD card has mip levels, except the radar tiles.

## Building mip levels for ETC1

- `rw::c3d::rasterGenerateCompressedMipmaps` decodes level 0, keeps its ETC
  bytes unchanged, and builds the smaller levels, then compresses them.
- Use a plain 2x2 box filter (`boxDownsample2x`). Do not use the 3x3
  `boxFilter` from `texMipmaps`. A 3x3 window on a 2x reduction blurs across
  tile edges and shifts the image by half a texel.
- The code builds the levels at load. The cache `models/txd.img` stores them, so
  the cost is paid once. A tile grows from 16 KB to about 21 KB.
- A change to texture conversion or compression needs a `CAPSVERSION` bump in
  `stories/src/rw/TexRead.cpp` (now 2), or the cache is never rebuilt on the
  console. A bump rebuilds the whole cache once on the next boot.
- Test: `scripts/tests/test_3ds_etc1_mipmaps.py`. It compiles the real
  `compress.cpp`.

## Radar tiles

`CTxdStore` (`stories/src/rw/TxdStore.cpp`, `PrepareRadarTxd`) builds the mips
for each `radarNN` TXD, marks the tile as shrink-protected and sets
`rwFILTERLINEAR`. The in-game bottom radar and the pause-menu map draw the same
tile rasters. A change to the tile filter or levels affects both. This
matches the PS2 sampler (bilinear with mip selection), which is set in the
per-frame setup at `0x100120`.

See `git log --grep="map tiles"`.
