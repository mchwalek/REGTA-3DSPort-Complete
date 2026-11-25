// Harness for test_tunnel_mouth_lod.py: the LODl_tunnel1 sector rule and
// crossfade from stories/src/renderer/Renderer.cpp are pasted in at the
// marker below.
#include "stubs.h"

/*@FUNCTION@*/

static float
Opacity(void)
{
	return LCSTunnelLodCrossfadeOpacity(gLCSTunnelLodListed, gLCSTunnelLodCrossfade);
}

int main()
{
	// PS2 SUBURB.LVZ lists the LOD east of the bend (x ~ -525) only.
	assert(IsLCSTunnelLodListedAt(CVector(-400.0f, 520.0f, 90.0f)));	// Section_01
	assert(IsLCSTunnelLodListedAt(CVector(-520.0f, 600.0f, 82.0f)));	// east of the bend
	assert(!IsLCSTunnelLodListedAt(CVector(-530.0f, 600.0f, 82.0f)));	// west of the bend
	assert(!IsLCSTunnelLodListedAt(CVector(-610.0f, 615.0f, 82.0f)));	// Section_02
	assert(!IsLCSTunnelLodListedAt(CVector(-718.5f, 620.0f, 82.0f)));	// Section_02/03 overlap
	assert(!IsLCSTunnelLodListedAt(CVector(-812.0f, 630.0f, 83.0f)));	// Section_03
	assert(!IsLCSTunnelLodListedAt(CVector(-900.0f, 610.0f, 83.0f)));	// at the west mouth
	// Outside the tunnel the normal LOD handoff stays.
	assert(IsLCSTunnelLodListedAt(CVector(-920.0f, 606.0f, 83.0f)));	// west of the mouth
	assert(IsLCSTunnelLodListedAt(CVector(-800.0f, 620.0f, 100.0f)));	// on the hill above
	assert(IsLCSTunnelLodListedAt(CVector(-800.0f, 575.0f, 83.0f)));	// south of Section_03

	// Steady state: the LOD is drawn east of the bend.
	const float ts = 2.0f;	// one PS2 frame at 25 fps
	UpdateLCSTunnelLodCrossfade(CVector(-520.0f, 600.0f, 82.0f), ts);
	assert(Opacity() == 1.0f);

	// Westbound: PS2 keeps the old sector's LOD for 8 frames, then fades it
	// out over 7 frames (0x200fb0, counter 479 - 32 per frame).
	const CVector west(-600.0f, 612.0f, 82.0f);
	float previous = 1.0f;
	for(int frame = 1; frame <= 16; frame++){
		UpdateLCSTunnelLodCrossfade(west, ts);
		const float opacity = Opacity();
		if(frame <= 8)
			assert(opacity == 1.0f);
		else if(frame <= 15){
			assert(opacity > 0.0f && opacity < previous);
		}else
			assert(opacity == 0.0f);
		previous = opacity;
	}
	UpdateLCSTunnelLodCrossfade(west, ts);
	assert(Opacity() == 0.0f);

	// Eastbound: the newly listed LOD fades in over the first 8 frames.
	const CVector east(-500.0f, 590.0f, 82.0f);
	previous = 0.0f;
	for(int frame = 1; frame <= 10; frame++){
		UpdateLCSTunnelLodCrossfade(east, ts);
		const float opacity = Opacity();
		if(frame < 8)
			assert(opacity > previous && opacity < 1.0f);
		else
			assert(opacity == 1.0f);
		previous = opacity;
	}

	// A crossing back during a fade restarts the crossfade, as on PS2.
	UpdateLCSTunnelLodCrossfade(west, ts);
	for(int frame = 0; frame < 10; frame++)
		UpdateLCSTunnelLodCrossfade(west, ts);
	assert(Opacity() > 0.0f && Opacity() < 1.0f);
	UpdateLCSTunnelLodCrossfade(east, ts);
	assert(Opacity() < 0.2f);

	// The fade runs on game time: at 30 fps (timestep 5/3) it lasts as long.
	for(int frame = 0; frame < 20; frame++)
		UpdateLCSTunnelLodCrossfade(east, ts);
	int frames = 0;
	do {
		UpdateLCSTunnelLodCrossfade(west, 5.0f / 3.0f);
		frames++;
	} while(Opacity() > 0.0f);
	assert(frames == 18 || frames == 19);
	return 0;
}
