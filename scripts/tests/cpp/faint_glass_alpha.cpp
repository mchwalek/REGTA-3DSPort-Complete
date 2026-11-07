// Harness for test_faint_glass_alpha.py: hasOnlyFaintAlpha/isFaintAlphaSource
// from common/librw/src/3ds/3dsraster.cpp and etc1Alpha4 from
// common/librw/src/3ds/tex/compress.cpp are pasted in at the markers below.
#include <cassert>
#include <cstdint>
#include <cstring>
#include "scenarios.h"
#define nil nullptr
typedef unsigned char uint8;
typedef unsigned int uint32;
enum GPU_TEXCOLOR { GPU_RGBA8, GPU_ETC1A4, GPU_RGB8 };
struct C3DRaster { GPU_TEXCOLOR format; bool hasAlpha; };

/*@RASTER@*/
/*@ALPHA4@*/

static void faint_alpha_detection() {
	uint8 etc[32];
	C3DRaster etcRas{GPU_ETC1A4, true};
	memset(etc, 0, sizeof(etc));
	assert(!hasOnlyFaintAlpha(&etcRas, etc, sizeof(etc)));  // fully transparent
	etc[3] = 0x45; etc[24] = 0x77;                           // colour bytes ignored
	etc[16 + 2] = 0x57;
	assert(hasOnlyFaintAlpha(&etcRas, etc, sizeof(etc)));
	etc[5] = 0x80;                                           // one texel at 136
	assert(!hasOnlyFaintAlpha(&etcRas, etc, sizeof(etc)));
	etc[5] = 0x08;
	assert(!hasOnlyFaintAlpha(&etcRas, etc, sizeof(etc)));
	C3DRaster noAlpha{GPU_ETC1A4, false};
	etc[5] = 0;
	assert(!hasOnlyFaintAlpha(&noAlpha, etc, sizeof(etc)));
	assert(!hasOnlyFaintAlpha(&etcRas, nil, 0));

	uint8 rgba[8] = {83, 255, 255, 255, 0, 255, 255, 255};  // ABGR
	C3DRaster rgbaRas{GPU_RGBA8, true};
	assert(hasOnlyFaintAlpha(&rgbaRas, rgba, sizeof(rgba)));
	rgba[4] = 128;
	assert(!hasOnlyFaintAlpha(&rgbaRas, rgba, sizeof(rgba)));

	C3DRaster rgbRas{GPU_RGB8, true};
	assert(!hasOnlyFaintAlpha(&rgbRas, rgba, sizeof(rgba)));
}

static void faint_alpha_rounds_in_etc1a4() {
	// izzy_dirtGlass alphas: flooring zeroed 3, 9, 11; rounding keeps 9 and 11.
	assert(etc1Alpha4(9, false) == 0 && etc1Alpha4(9, true) == 1);
	assert(etc1Alpha4(43, false) == 2 && etc1Alpha4(43, true) == 3);
	assert(etc1Alpha4(3, true) == 0 && etc1Alpha4(83, true) == 5);
	assert(etc1Alpha4(127, true) == 7);                      // stays below the faint limit
	assert(etc1Alpha4(255, true) == 15 && etc1Alpha4(255, false) == 15);

	uint8 px[2*12] = {};                                     // 2x2 RGBA, stride 12
	assert(!isFaintAlphaSource(px, 2, 2, 12));               // fully transparent
	px[3] = 83; px[11] = 200;                                // padding ignored
	assert(isFaintAlphaSource(px, 2, 2, 12));
	px[12 + 7] = 128;
	assert(!isFaintAlphaSource(px, 2, 2, 12));
}

int main(int argc, char **argv) {
	SCENARIOS_BEGIN
	SCENARIO(faint_alpha_detection)
	SCENARIO(faint_alpha_rounds_in_etc1a4)
	SCENARIOS_END
}
