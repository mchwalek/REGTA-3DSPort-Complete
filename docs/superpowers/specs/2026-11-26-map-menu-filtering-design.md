# Pause-menu map filtering (reLCS 3DS)

Trello: [Map filtering in map menu](https://trello.com/c/JncHEeIY/69-map-filtering-in-map-menu)
("It's nice that it's sharp, but it doesn't look good when zoomed out. We
probably need to apply some texture filtering").

## Problem

The pause-menu map draws the 128x128 `radarNN` tiles over the 320x220 atlas at
every zoom (`CRadar::DrawMenuMapSections3DS`, AGENTS.md #36). At the minimum
zoom a tile covers about 44 px of the top screen, so each screen pixel covers
about 3x3 texels. Roads and coastlines break up into stair steps and shimmer
while the map pans or zooms.

Two things cause it.

1. **The tiles are sampled with NEAREST.** `DrawMenuMapSections3DS` sets
   `rwRENDERSTATETEXTUREFILTER` to `rwFILTERLINEAR`, but the 3DS backend
   applies that state to the raster that is bound *at that moment*
   (`setRasterParams(0, ...)` in `common/librw/src/3ds/3dsdevice.cpp`).
   `TEXTURERASTER`, which `CSprite2d::Draw` uses to bind each tile, keeps the
   raster's own sampler. `allocateETC` creates every ETC raster with
   NEAREST/NEAREST, and `gForceCompression` makes every texture ETC. So the
   tiles stay NEAREST, and so does every other Im2D texture that nobody set
   while it was bound.
2. **The tiles have no mip levels.** All 10947 textures in the SD card's
   `gta3.img`, the radar tiles included, have one level, and so do the loose
   TXDs under `models/` and `txd/`. Bilinear filtering alone still drops
   texels at 3x minification.

## PS2 reference

Checked in `SLES_541.35` with REA:

- The map page draw (`0x33da58`) sets render states 7 and 2 through the
  setter `0x144b58`. Both fall to the default case there, so they do nothing.
- Textures bind through `0x321b50` → `0x144b58(1, raster)` → `0x2b5ad8`, which
  uploads the mip count (`flags >> 20 & 15`) and sets TEX0/MIPTBP
  (`0x29e338`).
- The per-frame setup `0x100120` sets TEX1 MMIN = 5 (`LINEAR_MIPMAP_NEAREST`)
  via `0x29ede8(0, 5)` and MMAG = 1 (`LINEAR`) via `0x29ee58(0, 1)`.
  `0x2ba340` sets both to 0 for a while and then restores 5/1.

So PS2 samples textures bilinear, with mip selection when a texture has
levels. I did not check whether the PS2 map texture has levels. The tiles on
the 3DS map are a port addition anyway (PS2 draws one sprite), so the PS2
data does not decide this.

## Design

### 1. Mip levels for the radar tiles (shared librw code, plus stories)

New backend function `rw::c3d::rasterGenerateCompressedMipmaps(Raster *)` in
`3dsraster.cpp`. For an ETC1 or ETC1A4 raster with one level and both sides
at least 16 px, it:

1. decodes level 0 to RGBA with `rg_etc1::unpack_etc1_block`, in the reverse
   order of `texCompress`/`etc1_common` (new `etc1_decode_common` and
   `etc1_decode` in `tex/compress.cpp`),
2. allocates a new `C3D_Tex` with the full chain through `TexAlloc` and copies
   the level-0 ETC bytes over unchanged,
3. builds each smaller level with a 2x2 box filter (new `boxDownsample2x`)
   and compresses it with the existing `texCompress`,
4. frees the old texture and sets `Raster::MIPMAP` in `raster->format`.

`CTxdStore` (`stories/src/rw/TxdStore.cpp`) calls it for each texture of a
`radarNN` TXD after the TXD loads, at the same places that call
`ProtectPlayerTxdFromShrinking`. It also marks the tile shrink-protected and
sets its filter to `rwFILTERLINEAR`.

The level-0 texels stay byte-identical, so a magnified tile looks exactly as
it does now.

### 2. Keep the mips in the texture cache

`CreateTxdImageForVideoCard` writes each TXD after it loads, so the cache
`models/txd.img` stores the tiles with their levels (`writeNativeTexture`
writes the format and the full size). `readNativeTexture` then allocates the
chain from the `MIPMAP` flag and reads it straight back, and the load hook
skips a tile that already has levels. `CAPSVERSION` goes from 1 to 2 so that
existing caches are rebuilt once.

### 3. Mip filter in the backend (shared librw code)

`updateRasterParams` now also sets the PICA mip filter. The unused
`filterConvMap_MIP` table becomes the mip-filter table. The texel column is
the existing `filterConvMap_NoMIP`, and both follow the gl3 backend's meaning
of the RW modes:

| RW filter | texel filter | mip filter |
|---|---|---|
| `NEAREST` | NEAREST | NEAREST |
| `LINEAR` | LINEAR | LINEAR |
| `MIPNEAREST` | NEAREST | NEAREST |
| `MIPLINEAR` | LINEAR | NEAREST |
| `LINEARMIPNEAREST` | NEAREST | LINEAR |
| `LINEARMIPLINEAR` | LINEAR | LINEAR |

The mip filter has no effect on a texture with one level, and no texture
loaded today has more than one, so only the radar tiles change.

New `rw::c3d::rasterSetFilterMode(Raster *, int32)` sets a raster's sampler
directly. When the raster is bound to a texture stage, it binds it again so
that citro3d uploads the new parameters.

## Rulings

- Ruling: generate the mips at load and keep them in `txd.img` — the tiles
  only exist as ETC data on the SD card, and decoding ETC is cheap, while
  re-encoding the small levels with `rg_etc1` low quality costs about 4 µs per
  block on a desktop CPU (340 blocks per tile), which is likely tens of ms per
  tile on the 3DS — if wrong, a tile loaded without the cache costs one such
  stall per load.
- Ruling: bump `CAPSVERSION` to 2 — without it, existing caches never get the
  levels and every tile load pays the encode — cost: one texture-cache rebuild
  on the first boot after the update (the version 1 bump set the precedent).
- Ruling: map RW `LINEAR` on a mipped raster to trilinear (mip filter LINEAR)
  — PICA always selects a level when a texture has levels, so a "no mip" mode
  cannot be expressed. The menu zooms continuously, and NEAREST mip selection
  would show a visible step at each level change. Radar code requests
  `rwFILTERLINEAR` everywhere, so a stray `TEXTUREFILTER` that lands on a tile
  keeps the same result — if wrong, the change is one table entry.
- Ruling: do not change `TEXTURERASTER` to apply the `TEXTUREFILTER` render
  state, as the gl3 backend does — that is the root bug, but the fix would
  change the filter of every Im2D draw (HUD, fonts, frontend) in all three
  games. This change sets the filter on the tiles only — cost if wrong: other
  Im2D textures stay NEAREST, as they are today.
- Ruling: set the tile filter at load, not in the menu draw — the in-game
  bottom-screen radar draws the same tile rasters and also requests
  `rwFILTERLINEAR`. Setting it only in the menu would leave a tile NEAREST or
  LINEAR depending on whether the menu was opened since it loaded — cost:
  the in-game radar tiles are now bilinear, which matches what the code asks
  for and what PS2 does.
- Ruling: mark the radar tiles shrink-protected — before this change they had
  no levels and `shrinkSomeTexture` could not touch them. Protection keeps
  that behaviour instead of letting memory pressure drop a tile's top level
  for good — cost: about 21 KB per loaded tile stays out of the last-resort
  shrink pool.
- Ruling: leave the 320x220 atlas unchanged — it shows only while tiles
  stream in, it is magnified (about 1.09x at minimum zoom), and the same
  texture draws the cold-start bottom-screen map, which a filter change would
  soften.
- Ruling: use a plain 2x2 box filter instead of the existing `boxFilter`
  (a 3x3 window, used by `texMipmaps`) — a 3x3 window on a 2x reduction
  blurs across tile edges and shifts the image by half a texel. Changing
  `texMipmaps` is out of scope (no caller uses it today).

## Testing

- Host test `scripts/tests/test_3ds_etc1_mipmaps.py` + `cpp/etc1_mipmaps.cpp`.
  It compiles the real `compress.cpp` and `rg_etc1.cpp`, encodes an image with
  the loop extracted from `texCompress`, decodes it with `etc1_decode`, and
  checks texel positions, colours within the ETC1 error, and exact 4-bit
  alpha. It also checks `boxDownsample2x`.
- `scripts/build.sh relcs` must build.
- On the console (not possible from this session): open the pause map at the
  minimum zoom and compare roads with the previous build. Zoom slowly to check
  that no level step shows. Check that the first boot rebuilds the texture
  cache once.

## Risks

- The cache rebuild takes time on the first boot after the update.
- If the cache cannot be written, each radar tile load re-encodes its levels
  (estimated tens of ms per tile). The map still works.
- A mipped tile uses about 21 KB instead of 16 KB.
