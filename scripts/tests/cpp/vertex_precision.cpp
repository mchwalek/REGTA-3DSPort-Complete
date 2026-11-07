// Harness for test_3ds_vertex_precision.py: translation-handling lines from
// setWorldMatrix() and beginUpdate() in common/librw/src/3ds/3dsdevice.cpp
// are pasted in at the markers below.
#include <cassert>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstring>

struct V3d { float x, y, z; };
struct Vec4 { float x, y, z, w; };
struct Mtx { Vec4 r[4]; };
struct RawMatrix { V3d pos; float posw; };
struct LTM { V3d pos; };
struct Frame { LTM ltm; LTM *getLTM() { return &ltm; } };
struct Camera { Frame frame; Frame *getFrame() { return &frame; } };

static V3d cameraWorldOrigin;
static RawMatrix raw;
static Mtx world;

/* Round a float32 to PICA200's float24 format: 1 sign + 7 exponent + 16
 * mantissa bits. Round-to-nearest over the 7 dropped mantissa bits. */
static float
round_float24(float v)
{
	if(v == 0.0f) return 0.0f;
	uint32_t bits;
	memcpy(&bits, &v, sizeof(bits));
	uint32_t sign = bits & 0x80000000u;
	int32_t  exp  = (bits >> 23) & 0xFFu;
	uint32_t mant = bits & 0x7FFFFFu;
	uint32_t rounded = (mant + (1u << 6)) >> 7;
	if(rounded > 0xFFFFu){
		rounded = 0;
		exp += 1;
	}
	uint32_t newbits = sign | ((uint32_t)exp << 23) | (rounded << 7);
	float result;
	memcpy(&result, &newbits, sizeof(result));
	return result;
}

static void
simulateWorldTranslation(void)
{
/*@WORLD_TRANSLATION@*/
}

static void
simulateBeginUpdateTranslation(Camera *cam, Mtx &view)
{
/*@CAMERA_CAPTURE@*/
/*@VIEW_TRANSLATION@*/
}

int main() {
	/* Before the fix: an absolute LCS world-space coordinate ~2300 units
	 * from origin (same order of magnitude as the ~2000-unit world span
	 * called out in the fix's background), rounded straight to float24
	 * the way the old code uploaded raw.pos directly. Crafted to land
	 * exactly on a float24 rounding half-step so the error is
	 * deterministic. */
	float absolute_pos = 2330.171875f;
	float rounded_absolute = round_float24(absolute_pos);
	float error_before_mm = std::fabs(rounded_absolute - absolute_pos) * 1000.0f;
	assert(error_before_mm > 10.0f);

	/* After the fix: camera and vertex are both far from the origin, but
	 * close to each other. beginUpdate() captures the camera position and
	 * zeroes u_view's translation... */
	Camera cam;
	cam.frame.ltm.pos = V3d{1234.5f, 0.0f, 0.0f};
	Mtx view;
	simulateBeginUpdateTranslation(&cam, view);
	assert(cameraWorldOrigin.x == 1234.5f);
	assert(view.r[0].w == 0.0f);
	assert(view.r[1].w == 0.0f);
	assert(view.r[2].w == 0.0f);
	assert(view.r[3].w == 1.0f);

	/* ...and setWorldMatrix() folds the camera position into u_world's
	 * translation, so only the small camera-relative delta ever reaches
	 * the float24 uniform. */
	raw.pos = V3d{1250.5003662109375f, 0.0f, 0.0f};
	raw.posw = 1.0f;
	simulateWorldTranslation();
	float delta = world.r[0].w;
	float rounded_delta = round_float24(delta);
	float error_after_mm = std::fabs(rounded_delta - delta) * 1000.0f;
	assert(error_after_mm < 0.2f);

	printf("error_before_mm=%f error_after_mm=%f\n", error_before_mm, error_after_mm);
}
