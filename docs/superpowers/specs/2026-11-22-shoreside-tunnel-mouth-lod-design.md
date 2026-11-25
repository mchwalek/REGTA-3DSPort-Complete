# Shoreside Vale northern tunnel: hide the west mouth LOD from inside the tunnel

Trello: [Strange opaque geometry in shoreside vale northern tunnel](https://trello.com/c/hmgOLkZ7).

> Correction (2026-11-25): PS2 drops this LOD at the tunnel bend, not only
> near the mouth, and fades it out. PS2 also keeps the `Trans_lights`
> instances for their glows. See
> `2026-11-25-shoreside-tunnel-glows-and-lod-crossfade-design.md`.

This follows `2026-11-21-shoreside-tunnel-light-volumes-design.md`. That fix
removed the `Trans_lights01-03` volumes. On the console the geometry was
still there and had turned from grey to black, so the volumes were only
blending over the real problem.

## Symptom

Reported on hardware, with the light-volume fix deployed:

1. Drive into the tunnel through its west mouth, the one after which the
   tunnel bends right. A moment after the entrance, black panels and a black
   wall across the road appear. The car drives through them.
2. Turn the camera back toward the entrance and they vanish.
3. Drive out through the same mouth and nothing shows.

## Cause

`LODl_tunnel1` (id 2806, txd `suburb1`, texture `tunnel_lod`, draw distance
3500) is the far-distance model of the west mouth. It holds the same portal
facade as the detailed `hill_tunnel1` (id 3171, draw distance 299), plus a
straight arch behind it: x -900.9..-880.2, y 582.7..633.7, z 76.9..89.9,
closed by an end wall at y 633.7. The arch has no floor and its faces point
inward. Its UVs sit on pure black texels, so from far away the mouth reads
as a dark hole.

The real tunnel (`Section_03` + `Section_3road`) is wider than that arch and
bends east. At y 625 it spans x -897..-860, and it continues past y 636. So
the arch walls and the end wall stand inside the drivable tunnel for about
50 m behind the mouth.

`CRenderer::SetupBigBuildingVisibility` (`stories/src/renderer/Renderer.cpp`)
hides a paired LOD inside its near distance only when
`HasVisibleLCSBuildingLodSource` finds the detailed model, and that list
holds only detailed entities that passed the on-screen test this frame. The
port does this on purpose so a block isn't left empty when its detailed
model isn't drawn. Inside the tunnel, looking ahead, `hill_tunnel1` is
behind the camera. It isn't in the list, so the LOD draws. That matches all
three observations.

## What PS2 does

PS2 has the same LOD with the same arch: `SUBURB.LVZ` LOD id 0xf0f, resource
2635, bound (-890, 599, 79.2) r 36.4. Each sector lists what it draws. Of
745 sectors, 678 list the LOD and 51 list the detailed portal (id 0x8720).
No sector lists both. The LOD is missing from the whole block of sectors
around the mouth, so PS2 never draws it from inside or near the tunnel,
whichever way the camera looks. The east mouth is the same (LOD 0xf10 in
679 sectors, portal 0x871f in 50, none shared).

## Fix

On `_3DS` builds of stories, never draw `LODl_tunnel1` while the camera is
within the LOD's bounding sphere plus 10 m. The sphere is centred on
(-890.2, 600.9, 83.5) with radius 38.1, so the limit is 48.1 m.

- The whole arch is inside the sphere (its farthest corner is 34.9 m from
  the centre), and its inward faces can only be seen from inside it or
  through the mouth. Through the mouth the detailed portal is on screen and
  the existing rule already hides the LOD.
- The check is one helper in `Renderer.cpp`,
  `IsCameraInsideLCSTunnelLod(int modelId, const LCSWorldBounds &bounds)`,
  called at the top of `SetupBigBuildingVisibility`. The model id is looked
  up by name once in `CRenderer::Init`, the way `Streaming.cpp` resolves the
  island LODs.
- Within 48.1 m of that centre the detailed portal is at most about 27 m
  away from the camera by surface distance. Its contracted 3DS draw range is
  larger than that in every profile, so the facade is still drawn by
  `hill_tunnel1` whenever it is on screen.

Only stories changes. `LODl_tunnel2`, the east mouth LOD, has no arch (its
bounds equal the detailed portal's), so it is left alone.

## Not changed

- The general handoff for the other LOD pairs. PS2's rule ("the LOD is
  never listed where the detailed model is") would hide every paired LOD
  near the camera. On 3DS the detailed range is contracted, and a scan of
  the IPL data found 114 of 786 name-matched pairs whose LOD reaches more
  than 10 m outside the detailed model's bounds. Applying the rule to all of
  them risks holes.
- The LOD model itself. A patched DFF in `PORTFIX.IMG` without the arch
  needs an SD update and a new install manifest, and PS2's model has the
  arch too.
- The `Trans_lights` removal from the first fix. PS2 has no such instances.

## Testing

- Host test `scripts/tests/test_tunnel_mouth_lod.py` extracts the helper and
  checks: camera inside the arch hides the LOD, 47 m hides it, 49 m and
  150 m draw it, another model at distance 0 draws, and an unresolved model
  id never hides anything.
- `scripts/build.sh relcs`, the full Python suite and
  `scripts/verify-layout.sh`.
- On the console: drive in through the west mouth looking ahead, and stop
  inside the first 50 m and turn the camera all the way round. No black
  panels. From outside, far and near, the mouth still looks the same.

## Rulings

- Ruling: fix by model name for this one LOD — it is the only confirmed case and the general rule risks holes elsewhere — cost if wrong: another LOD with interior geometry needs its own entry.
- Ruling: limit is bounding sphere + 10 m — the sphere contains the whole arch and the margin costs nothing because the detailed portal is in range there — cost if wrong: too small shows the arch at the edge, too large is harmless up to the portal's draw range.
- Ruling: keep commit `626e49f` — PS2 has no `Trans_lights` instances — cost if wrong: the tunnel lacks a night glow that PS2 doesn't have either.

## Known cost

If the player is placed next to the mouth before `hill_tunnel1` has
streamed in (a teleport or a save load), the facade is missing until it
loads. PS2 behaves the same way there.
