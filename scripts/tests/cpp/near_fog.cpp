// Harness for test_3ds_near_fog.py: common/3ds/PS2GraphicsProfile.h is pasted in
// at the marker below (the header is self-contained).
#include <cassert>
#include <cmath>
#include <cstdio>

/*@PROFILE@*/

using namespace PS2Graphics3DS;

static bool near(float a, float b) { return std::fabs(a - b) < 1e-4f; }

int main() {
	assert(near(SilhouetteFogStart(-266.0f, 84.0f), 84.0f * 0.55f));
	assert(near(SilhouetteFogStart(50.0f, 84.0f), 50.0f));

	const float authored[] = {0.0f, 30.0f, 60.0f, 200.0f};
	for(float a : authored){
		const float start = FogStart(a, 84.0f, 1.0f, true);
		assert(near(SilhouetteFogStart(start, 84.0f), start));
	}

	assert(SilhouetteWeight(10.0f, SilhouetteFogStart(-266.0f, 84.0f), 84.0f, LibertyCityStories) == 0.0f);
	assert(SilhouetteWeight(10.0f, -266.0f, 84.0f, LibertyCityStories) > 0.0f);

	assert(FogVisibility(0.0f, -266.0f, 84.0f) < 0.5f);
	printf("ok\n");
	return 0;
}
