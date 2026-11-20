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
	// Ped/car light: 2*ambient + sun scaled by view angle, clamped at 1.
	assert(near(EntityLightChannel(12.0f / 255.0f, 166.0f / 255.0f, -1.0f), 2.0f * 12.0f / 255.0f));
	assert(EntityLightChannel(66.0f / 255.0f, 1.0f, 1.0f) == 1.0f);
	assert(std::fabs(EntityLightChannel(66.0f / 255.0f, 1.0f, 0.0f) - (2.0f * 66.0f / 255.0f + 0.1675f)) < 1e-4f);
	float prev = EntityLightChannel(0.1f, 0.8f, -1.0f);
	for(int i = 1; i <= 20; i++){
		const float v = EntityLightChannel(0.1f, 0.8f, -1.0f + 0.1f * i);
		assert(v >= prev);
		prev = v;
	}
	printf("ok\n");
	return 0;
}
