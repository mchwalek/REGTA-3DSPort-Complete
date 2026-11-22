// Harness for test_tunnel_mouth_lod.py: IsCameraInsideLCSTunnelLod from
// stories/src/renderer/Renderer.cpp is pasted in at the marker below.
#include "stubs.h"

struct LCSWorldBounds {
	CVector offset;
	float radius, distance;
};

static int gLCSTunnelMouthLod = -1;
static const float LCS_TUNNEL_LOD_MARGIN = 10.0f;

/*@FUNCTION@*/

int main()
{
	gLCSTunnelMouthLod = 2806;
	assert(IsCameraInsideLCSTunnelLod(2806, {{}, 38.1f, 19.6f}));	// inside the arch
	assert(IsCameraInsideLCSTunnelLod(2806, {{}, 38.1f, 34.9f}));	// far corner of the arch
	assert(IsCameraInsideLCSTunnelLod(2806, {{}, 38.1f, 47.0f}));
	assert(!IsCameraInsideLCSTunnelLod(2806, {{}, 38.1f, 49.0f}));
	assert(!IsCameraInsideLCSTunnelLod(2806, {{}, 38.1f, 150.0f}));
	assert(!IsCameraInsideLCSTunnelLod(2805, {{}, 38.1f, 0.0f}));	// other model
	gLCSTunnelMouthLod = -1;
	assert(!IsCameraInsideLCSTunnelLod(2806, {{}, 38.1f, 0.0f}));	// name not found
	return 0;
}
