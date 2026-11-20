// Harness for test_3ds_lcs_lighting.py: common/3ds/PS2GraphicsProfile.h is pasted in
// at the marker below (the header is self-contained).
#include <cassert>
#include <cmath>
#include <cstdio>

/*@PROFILE@*/

using namespace PS2Graphics3DS;

static bool near(float a, float b) { return std::fabs(a - b) < 1e-5f; }

int main() {
	// colourfilterLCS.frag adds the whole blur: gain = 1 + colour.
	assert(near(ColourGain(LibertyCityStories, 238.0f), 1.0f + 238.0f / 255.0f));
	assert(near(ColourGain(LibertyCityStories, 0.0f), 1.0f));
	assert(near(ColourGain(LibertyCityStories, 300.0f), 2.0f));

	// Fog compensation must cancel the grade exactly.
	const float colours[] = {0.0f, 128.0f, 238.0f, 255.0f};
	for(float c : colours)
		assert(near(FogColourCompensation(LibertyCityStories, c, ColourGain(LibertyCityStories, c)), 1.0f));

	// III/VC values produced by the header before the LCS change.
	assert(near(ColourGain(GTAIII, 100.0f, 30.0f), 0.925030231f));
	assert(near(ColourGain(ViceCity, 100.0f), 3.96669436f));
	printf("ok\n");
	return 0;
}
