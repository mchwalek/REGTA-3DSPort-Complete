# Shoreside Vale northern tunnel: drop the light volumes PS2 never placed

Trello: [Strange opaque geometry in shoreside vale northern tunnel](https://trello.com/c/hmgOLkZ7). The card has no description or screenshot.

> Correction (2026-11-25): PS2 does place these instances. `GAME.DTZ` holds
> them as buildings with 30 coronastar glows; only `SUBURB.LVZ` has no mesh
> for them. Skipping them at load time also removed the glows. The fix now
> skips only the mesh draw. See
> `2026-11-25-shoreside-tunnel-glows-and-lod-crossfade-design.md`.

## What the 3DS draws there

The tunnel through the hill north of Shoreside Vale (y 450-770) is built from
these `suburb.ipl` instances (txd `sjl_tunnel`):

| Model | Role |
|---|---|
| `Section_01/02/03` | tunnel walls |
| `Section_1road/2road/3road` | road surface |
| `hill_tunnel1/2` + `LODl_tunnel1/2` | portals |
| `dead_end` | closed side branch |
| `Trans_lights01/02/03` (ids 3118/3117/3116) | light volumes |

`Trans_lights01-03` are three meshes that fill the tunnel volume, about 160 m
long each. Their IDE flags are 76 (draw last, additive, no z-write). Their
one texture, `Tunnel_White_SJL`, is white with alpha 0-39. Day prelight is
black and night prelight goes up to RGB 190. They have no collision.

On 3DS they don't render as a glow:

- `CVisibilityPlugins::RenderFadingEntities` applies `DESTBLEND = ONE` only
  while an entity distance-fades. Close up, the volumes use normal
  `SRCALPHA/INVSRCALPHA` blending.
- LCS building lighting (`prelight * Ambient + Ambient_Bl/2`, doubled on
  textured texels) gives them a grey base colour even with black day
  prelight.

The result is grey slabs inside the tunnel. A console test after the fix
showed that the reported geometry was still there and had turned black. The
slabs were blending over it. The cause of the report is the west mouth LOD:
see `2026-11-22-shoreside-tunnel-mouth-lod-design.md`.

## What PS2 draws there

The PS2 static world is in `/MODELS/SUBURB.LVZ` + `SUBURB.IMG`. Each sector
lists its instances in pass lists (0 SUPERLOD, 1 LOD, 2 ROADS, 3 NORMAL,
4 NOZWRITE, 5 LIGHTS, 6 TRANSPARENT). Instance bounds are world-space
spheres, so they can be matched against the IPL positions.

Every PS2 instance whose bound centre is within 40 m of a `Trans_lights`
position belongs to one of the other tunnel models:

| PS2 id | Resource | List | Bound centre | Matches |
|---|---|---|---|---|
| 0x869f / 0x869e / 0x8721 | 1494 / 1488 / 1599 | 3 | (-379, 505) / (-811, 618) / (-599, 621) | `Section_01/03/02` (24-48 meshes, tex 1489-1493) |
| 0x8a49 / 0x8a4a / 0x8a4b | 2097 / 2098 / 2099 | 3 | next to each section | `Section_Nroad` (2-4 meshes, opaque tex 186) |
| 0x8721 | 1605 | 6 | (-599, 621) | two small alpha quads of `Section_02` |
| 0x840d | 872 | 3 | (-337, 519), r 185 | hill terrain |

Other matches: `dead_end` is 0x871e at (-673, 739), the portals are
0x871f/0x8720, and the portal LODs are 0xf0f/0xf10 in list 1. No instance in
any list (including LIGHTS, which PS2 draws additively: `0x2008b8` case 5,
`0x201310`, `SRCBLEND 5 / DESTBLEND 2`) has a texture like
`Tunnel_White_SJL` or sits on the light volumes. A float scan of the LVZ and
the IMG for the three world positions finds nothing. PS2 simply has no
light volumes in this tunnel. Its LIGHTS list in `SUBURB.LVZ` holds 32
instances, none of them near the tunnel.

## Fix

Don't create the `Trans_lights01`, `Trans_lights02` and `Trans_lights03`
instances when `suburb.ipl` loads, on `_3DS` builds of stories.

- The check is by model name, case-insensitive, in
  `CFileLoader::LoadObjectInstance` (`stories/src/core/FileLoader.cpp`),
  before the entity is created. It's a small helper,
  `IsInstanceAbsentOnPS2(const char *modelName)`, so a host test can call it.
- Names, not ids: the ids come from the SD IDE files and can change with the
  data. The names are the ones the PS2 comparison found.
- Code, not data: an edited `suburb.ipl` in `gamefiles/` needs the two
  allow-list edits (AGENTS.md landmine 5), an SD update and a new install
  manifest. A `3dslink` deploy doesn't push SD files, so a code fix reaches
  the console with the executable alone.
- The models have no collision, so the only change is that nothing draws
  there.

Only stories changes. III and miami have no such models.

## Not changed

- The additive-only-while-fading behaviour in `RenderFadingEntities`. Other
  flag-76 models (commer `comlights*`, indust `lc_indwindows*`) go through
  the same path. Changing it needs its own PS2 check of each of them.
- The LOD, portal, section and road models. Each has a PS2 counterpart.

## Testing

- Host test `scripts/tests/test_ps2_absent_instances.py` extracts
  `IsInstanceAbsentOnPS2` and checks it matches the three names in any case
  and rejects other tunnel models (`Section_01`, `Section_1road`,
  `hill_tunnel1`, `LODl_tunnel1`, `dead_end`), a longer name that starts
  with one of the three (`Trans_lights01b`), and the empty string.
- `scripts/build.sh relcs`, the full Python suite and
  `scripts/verify-layout.sh`.
- On the console: drive through the tunnel by day and by night. Nothing
  should hang in the air between the walls.

## Rulings

- Ruling: treat `Trans_lights01-03` as the reported geometry — they are the only tunnel models with no PS2 counterpart — this was wrong: the console test showed the report is the west mouth LOD. The removal stays because PS2 has no such instances.
- Ruling: remove the instances instead of fixing the additive blend — PS2 has no such instances at all, so removing them matches PS2 by day and by night — cost if wrong: none for PS2 parity. The PC data's night glow is gone.
- Ruling: gate on `_3DS` — the only build this repo makes, and desktop reLCS's additive pipeline may draw them differently — cost if wrong: a desktop build keeps the volumes.
