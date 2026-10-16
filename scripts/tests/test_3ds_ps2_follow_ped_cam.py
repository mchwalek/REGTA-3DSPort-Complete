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

    def test_string_dist_clamps_to_zoom_range(self):
        driver = r"""
int main(){
	assert(Abs(PS2FollowPedStringDist(1.0f, 0.25f) - 2.0f) < 0.0001f);
	assert(Abs(PS2FollowPedStringDist(100.0f, 0.25f) - 2.25f) < 0.0001f);
	assert(Abs(PS2FollowPedStringDist(2.1f, 0.25f) - 2.1f) < 0.0001f);
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


if __name__ == "__main__":
    unittest.main()
