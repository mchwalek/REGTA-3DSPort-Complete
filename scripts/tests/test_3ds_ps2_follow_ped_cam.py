"""Host-compiled tests for the PS2-ported MODE_FOLLOWPED pure-math helpers
in stories/src/core/Cam.cpp (CCam::Process_FollowPed_Rotation). Each helper
is extracted verbatim from the real source file and compiled+run standalone,
so these tests exercise the exact code that ships on-device, not a
reimplementation. See
docs/superpowers/specs/2026-10-16-ps2-on-foot-camera-design.md for the
derivation of every constant asserted below.
"""
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CAM_CPP = ROOT / "stories" / "src" / "core" / "Cam.cpp"

STUB_PRELUDE = r"""
#include <cassert>
#include <cmath>
#include <cstdio>

static inline float Abs(float x) { return x < 0.0f ? -x : x; }
static inline float Pow(float base, float exp) { return powf(base, exp); }
template<class T> static inline T Min(T a, T b) { return a < b ? a : b; }
template<class T> static inline T Max(T a, T b) { return a > b ? a : b; }
#define DEGTORAD(x) ((x) * 3.14159265358979323846f / 180.0f)

"""


def extract_function(source: str, signature: str) -> str:
    start = source.index(signature)
    end = source.index("\n}\n", start) + len("\n}\n")
    return source[start:end]


def build_and_run(cpp_source: str) -> str:
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "test.cpp"
        binary = Path(tmp) / "test"
        path.write_text(cpp_source)
        subprocess.run(
            ["c++", "-std=c++11", "-fsanitize=address,undefined", str(path), "-o", str(binary)],
            check=True,
        )
        result = subprocess.run([str(binary)], check=True, capture_output=True, text=True)
        return result.stdout


class TestPS2FollowPedHelpers(unittest.TestCase):
    def setUp(self):
        self.source = CAM_CPP.read_text()

    def _run(self, signature: str, driver: str) -> str:
        fn = extract_function(self.source, signature)
        return build_and_run(STUB_PRELUDE + fn + "\n\n" + driver)

    def test_look_down_per_zoom(self):
        driver = r"""
int main(){
	float z1 = PS2FollowPedLookDown(0.06f);
	float z2 = PS2FollowPedLookDown(-0.1f);
	float z3 = PS2FollowPedLookDown(-0.07f);
	assert(Abs(z1 - 0.21f) < 0.001f);
	assert(Abs(z2 - 0.05f) < 0.001f);
	assert(Abs(z3 - 0.08f) < 0.001f);
	printf("ok\n");
	return 0;
}
"""
        out = self._run("float\nPS2FollowPedLookDown(", driver)
        self.assertEqual(out.strip(), "ok")

    def test_string_dist_follows_zoom(self):
        driver = r"""
int main(){
	// Zoom growing (Select zoom-out) pushes out even with a short string.
	assert(Abs(PS2FollowPedStringDist(2.25f, 2.5f, 2.25f) - 4.5f) < 0.0001f);
	// Zoom shrinking pulls straight in.
	assert(Abs(PS2FollowPedStringDist(4.5f, 0.0f, 4.5f) - 2.0f) < 0.0001f);
	// Steady zoom: string length kept within [2, maxDist].
	assert(Abs(PS2FollowPedStringDist(3.0f, 2.5f, 4.5f) - 3.0f) < 0.0001f);
	assert(Abs(PS2FollowPedStringDist(1.0f, 2.5f, 4.5f) - 2.0f) < 0.0001f);
	assert(Abs(PS2FollowPedStringDist(9.0f, 2.5f, 4.5f) - 4.5f) < 0.0001f);
	// maxDist == 2: always 2.
	assert(Abs(PS2FollowPedStringDist(1.0f, 0.0f, 2.0f) - 2.0f) < 0.0001f);
	printf("ok\n");
	return 0;
}
"""
        out = self._run("float\nPS2FollowPedStringDist(", driver)
        self.assertEqual(out.strip(), "ok")

    def test_pitch_step_converges_and_respects_cap(self):
        driver = r"""
int main(){
	// Far from target: step is capped at 0.1*dt.
	float a = PS2FollowPedPitchStep(1.0f, 0.0f, 1.0f);
	assert(Abs(a - 0.1f) < 0.0001f);
	// Already at target: no movement.
	float b = PS2FollowPedPitchStep(0.3f, 0.3f, 1.0f);
	assert(Abs(b - 0.3f) < 0.0001f);
	// dt = 0 is a no-op.
	float c = PS2FollowPedPitchStep(1.0f, 0.2f, 0.0f);
	assert(Abs(c - 0.2f) < 0.0001f);
	printf("ok\n");
	return 0;
}
"""
        out = self._run("float\nPS2FollowPedPitchStep(", driver)
        self.assertEqual(out.strip(), "ok")

    def test_stick_target_is_quadratic_and_signed(self):
        driver = r"""
int main(){
	float gain = 1.0f/1120.0f;
	float pos = PS2FollowPedStickTarget(64.0f, gain, 70.0f);
	float neg = PS2FollowPedStickTarget(-64.0f, gain, 70.0f);
	assert(Abs(pos - 0.007f*0.007f*64.0f*64.0f*gain*70.0f) < 0.00001f);
	assert(Abs(pos + neg) < 0.00001f);
	// Doubling the deflection quadruples the target.
	assert(Abs(PS2FollowPedStickTarget(128.0f, gain, 70.0f) - 4.0f*pos) < 0.00001f);
	assert(PS2FollowPedStickTarget(0.0f, gain, 70.0f) == 0.0f);
	printf("ok\n");
	return 0;
}
"""
        out = self._run("float\nPS2FollowPedStickTarget(", driver)
        self.assertEqual(out.strip(), "ok")

    def test_speed_step_smooths_clamps_and_snaps(self):
        driver = r"""
int main(){
	// Target clamped to 0.1, then blended at (1-0.8^dt).
	assert(Abs(PS2FollowPedSpeedStep(1.0f, 0.0f, 1.0f) - 0.02f) < 0.0001f);
	assert(Abs(PS2FollowPedSpeedStep(-1.0f, 0.0f, 1.0f) + 0.02f) < 0.0001f);
	// No target: previous speed decays by 0.8^dt instead of stopping dead.
	assert(Abs(PS2FollowPedSpeedStep(0.0f, 0.05f, 1.0f) - 0.04f) < 0.0001f);
	// Tiny speed snaps to zero.
	assert(PS2FollowPedSpeedStep(0.0f, 0.0001f, 1.0f) == 0.0f);
	printf("ok\n");
	return 0;
}
"""
        out = self._run("float\nPS2FollowPedSpeedStep(", driver)
        self.assertEqual(out.strip(), "ok")

    def test_auto_rotate_step_caps_and_thresholds(self):
        driver = r"""
int main(){
	// Stopped ped: no auto-rotate.
	assert(Abs(PS2FollowPedAutoRotateStep(1.0f, 0.0f, 1.0f, false)) < 0.0001f);
	// Already behind: no auto-rotate.
	assert(Abs(PS2FollowPedAutoRotateStep(0.0f, 5.0f, 1.0f, false)) < 0.0001f);
	// Fast-moving ped, big delta: capped at 0.02*dt.
	float step = PS2FollowPedAutoRotateStep(1.0f, 10.0f, 1.0f, false);
	assert(Abs(step - 0.02f) < 0.0001f);
	// Sign follows betaDelta.
	float negStep = PS2FollowPedAutoRotateStep(-1.0f, 10.0f, 1.0f, false);
	assert(Abs(negStep + 0.02f) < 0.0001f);
	// Small delta: proportional, so it settles instead of overshooting.
	assert(Abs(PS2FollowPedAutoRotateStep(0.01f, 10.0f, 1.0f, false) - 0.01f) < 0.0001f);
	assert(Abs(PS2FollowPedAutoRotateStep(0.01f, 2.0f, 1.0f, false) - 0.002f) < 0.0001f);
	// Ped walking at the camera (>=170deg): no auto-rotate.
	assert(PS2FollowPedAutoRotateStep(DEGTORAD(171.0f), 10.0f, 1.0f, false) == 0.0f);
	// Force-behind latch: ignores ped speed, doubles the cap, no 170deg cutoff.
	assert(Abs(PS2FollowPedAutoRotateStep(1.0f, 0.0f, 1.0f, true) - 0.04f) < 0.0001f);
	assert(Abs(PS2FollowPedAutoRotateStep(0.2f, 0.0f, 1.0f, true) - 0.02f) < 0.0001f);
	assert(Abs(PS2FollowPedAutoRotateStep(DEGTORAD(171.0f), 0.0f, 1.0f, true) - 0.04f) < 0.0001f);
	printf("ok\n");
	return 0;
}
"""
        out = self._run("float\nPS2FollowPedAutoRotateStep(", driver)
        self.assertEqual(out.strip(), "ok")

    def test_level_pitch_eases_toward_level(self):
        driver = r"""
int main(){
	assert(Abs(PS2FollowPedLevelPitch(0.5f, 1.0f) - 0.45f) < 0.0001f);
	assert(Abs(PS2FollowPedLevelPitch(-1.0f, 1.0f) + 0.9f) < 0.0001f);
	// Capped at 0.16*dt.
	assert(Abs(PS2FollowPedLevelPitch(10.0f, 1.0f) - 9.84f) < 0.0001f);
	assert(PS2FollowPedLevelPitch(0.0f, 1.0f) == 0.0f);
	printf("ok\n");
	return 0;
}
"""
        out = self._run("float\nPS2FollowPedLevelPitch(", driver)
        self.assertEqual(out.strip(), "ok")


if __name__ == "__main__":
    unittest.main()
