// Harness for test_tunnel_light_meshes.py: IsLCSMeshlessLightModel from
// stories/src/renderer/Renderer.cpp is pasted in at the marker below.
#include "stubs.h"

/*@FUNCTION@*/

int main()
{
	// Names not found yet: no model is meshless.
	assert(!IsLCSMeshlessLightModel(0));
	assert(!IsLCSMeshlessLightModel(-1));

	gLCSMeshlessLightModels[0] = 3116;
	gLCSMeshlessLightModels[1] = 3117;
	gLCSMeshlessLightModels[2] = 3118;
	assert(IsLCSMeshlessLightModel(3116));
	assert(IsLCSMeshlessLightModel(3117));
	assert(IsLCSMeshlessLightModel(3118));
	assert(!IsLCSMeshlessLightModel(3115));
	assert(!IsLCSMeshlessLightModel(3119));
	assert(!IsLCSMeshlessLightModel(-1));

	// One name not found: only the others are meshless.
	gLCSMeshlessLightModels[1] = -1;
	assert(!IsLCSMeshlessLightModel(-1));
	assert(!IsLCSMeshlessLightModel(3117));
	assert(IsLCSMeshlessLightModel(3118));
	return 0;
}
