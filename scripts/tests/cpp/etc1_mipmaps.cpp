// Harness for test_3ds_etc1_mipmaps.py. The test links the real
// common/librw/src/3ds/tex/compress.cpp and rg_etc1.cpp, and pastes the tile
// loop of texCompress (3dsraster.cpp) in at the marker below.
#include <cassert>
#include <cstdint>
#include <cstdlib>
#include <cstring>
#include <vector>
#include "scenarios.h"

namespace rw {
namespace c3d {
void etc1_common(uint8_t *src, uint8_t **dst, int stride, bool alpha, bool roundAlpha);
void etc1_decode(const uint8_t *src, uint8_t *dst, int width, int height, bool alpha);
void boxDownsample2x(const uint8_t *src, uint8_t *dst, int width, int height);
}
}
using namespace rw::c3d;
typedef uint8_t uint8;

// Encode a whole image in the block order of texCompress.
static std::vector<uint8> encode(uint8 *src, int width, int height, bool alpha) {
	std::vector<uint8> out(alpha ? width * height : width * height / 2);  // ETC1A4 8 bpp, ETC1 4 bpp
	uint8 *dst = out.data();
	int stride = width * 4;
	bool roundAlpha = false;
	/*@TILE_LOOP@*/
	assert(dst == out.data() + out.size());
	return out;
}

// One solid colour per 4x4 block, distinct per block, so a block in the wrong
// place shows up as a large error. ETC1 codes a solid block almost exactly.
static void fill_blocks(uint8 *px, int width, int height) {
	for (int y = 0; y < height; y++)
		for (int x = 0; x < width; x++) {
			int bx = x / 4, by = y / 4;
			uint8 *p = &px[(y * width + x) * 4];
			p[0] = (uint8)(16 + bx * 53 + by * 7);
			p[1] = (uint8)(240 - by * 37 - bx * 5);
			p[2] = (uint8)((bx * 29 + by * 61) & 0xFF);
			p[3] = (uint8)(17 * ((x + 3 * y) & 15));  // per-texel alpha, exact in 4 bits
		}
}

static void round_trip(bool alpha) {
	const int w = 16, h = 16;
	uint8 src[w * h * 4], dec[w * h * 4];
	fill_blocks(src, w, h);
	std::vector<uint8> etc = encode(src, w, h, alpha);
	memset(dec, 0xCD, sizeof(dec));
	etc1_decode(etc.data(), dec, w, h, alpha);
	for (int i = 0; i < w * h; i++) {
		for (int c = 0; c < 3; c++)
			assert(abs(dec[i * 4 + c] - src[i * 4 + c]) <= 8);
		assert(dec[i * 4 + 3] == (alpha ? src[i * 4 + 3] : 255));
	}
}

static void decode_round_trips_etc1a4() { round_trip(true); }

static void decode_round_trips_etc1() { round_trip(false); }

static void downsample_averages_2x2() {
	uint8 src[4 * 2 * 4], dst[2 * 1 * 4];
	for (int i = 0; i < (int)sizeof(src); i++) src[i] = (uint8)(i * 9);
	boxDownsample2x(src, dst, 4, 2);
	for (int x = 0; x < 2; x++)
		for (int c = 0; c < 4; c++) {
			int sum = src[(2 * x) * 4 + c] + src[(2 * x + 1) * 4 + c] +
			          src[16 + (2 * x) * 4 + c] + src[16 + (2 * x + 1) * 4 + c];
			assert(dst[x * 4 + c] == (sum + 2) / 4);
		}
}

int main(int argc, char **argv) {
	SCENARIOS_BEGIN
	SCENARIO(decode_round_trips_etc1a4)
	SCENARIO(decode_round_trips_etc1)
	SCENARIO(downsample_averages_2x2)
	SCENARIOS_END
}
