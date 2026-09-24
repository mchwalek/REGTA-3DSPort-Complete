#!/usr/bin/env python3
"""Regression test for the 3DS free-aim point's vertical/yaw update
(Update3DSFreeAimPointAngles in stories/src/core/Cam.cpp).

Extracts the real function body, compiles it against a minimal C++ stub
standing in for CVector/CGeneral, and asserts the PS2-derived pitch envelope
(50-110 degrees from the ped's vertical, with accept/reject hysteresis) and
yaw cone (+-110 degrees off the ped's forward, same hysteresis pattern).
"""
import math
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CAM_CPP = ROOT / "stories" / "src" / "core" / "Cam.cpp"


def extract_function(source: str, signature: str) -> str:
    """Extract a verbatim function body starting at `signature`, ending at the
    next column-zero closing brace."""
    start = source.index(signature)
    end = source.index("\n}\n", start) + len("\n}\n")
    return source[start:end]


def build_and_run(cpp_source: str) -> str:
    with tempfile.TemporaryDirectory(prefix="regta-free-aim-point-test-") as tmp:
        path = Path(tmp) / "test_free_aim_point.cpp"
        binary = Path(tmp) / "test_free_aim_point"
        path.write_text(cpp_source)
        subprocess.run(
            ["c++", "-std=c++11", "-fsanitize=address,undefined",
             str(path), "-o", str(binary)],
            check=True,
        )
        result = subprocess.run([str(binary)], check=True, capture_output=True, text=True)
        return result.stdout


STUB_PRELUDE = r"""
#include <cassert>
#include <cmath>
#include <cstdio>

#define PI 3.14159265358979323846f
#define DEGTORAD(x) ((x)*PI/180.0f)
#define RADTODEG(x) ((x)*180.0f/PI)

static float Acos(float v){ return acosf(v); }
static float Cos(float v){ return cosf(v); }
static float Sin(float v){ return sinf(v); }
static float Abs(float v){ return fabsf(v); }
static float Clamp(float v, float lo, float hi){ return v < lo ? lo : (v > hi ? hi : v); }

struct CVector {
	float x, y, z;
	CVector() : x(0.0f), y(0.0f), z(0.0f) {}
	CVector(float x_, float y_, float z_) : x(x_), y(y_), z(z_) {}
	CVector operator+(const CVector &v) const { return CVector(x+v.x, y+v.y, z+v.z); }
	CVector operator-(const CVector &v) const { return CVector(x-v.x, y-v.y, z-v.z); }
	CVector operator*(float f) const { return CVector(x*f, y*f, z*f); }
	float Magnitude() const { return sqrtf(x*x + y*y + z*z); }
	void Normalise() { float m = Magnitude(); if(m > 1e-6f){ x /= m; y /= m; z /= m; } }
};

struct CGeneral {
	static float GetATanOfXY(float x, float y){
		float arc = atan2f(y, x);
		if(arc < 0.0f) arc += 2.0f*PI;
		return arc;
	}
	static float LimitRadianAngle(float angle){
		float result = angle;
		if(result < -25.0f) result = -25.0f;
		if(result > 25.0f) result = 25.0f;
		while(result >= PI) result -= 2.0f*PI;
		while(result < -PI) result += 2.0f*PI;
		return result;
	}
};

"""


def pitch_from_ped(point: "tuple", ped_pos: "tuple") -> float:
    dx = point[0]-ped_pos[0]; dy = point[1]-ped_pos[1]; dz = point[2]-ped_pos[2]
    mag = math.sqrt(dx*dx+dy*dy+dz*dz)
    return math.degrees(math.acos(max(-1.0, min(1.0, dz/mag))))


class Test3DSFreeAimPointAngles(unittest.TestCase):
    def _extract(self) -> str:
        source = CAM_CPP.read_text()
        fn = extract_function(
            source,
            "static void\nUpdate3DSFreeAimPointAngles(",
        )
        return fn

    def _run_scenario(self, driver_main: str) -> str:
        fn = self._extract()
        cpp = STUB_PRELUDE + fn + "\n\n" + driver_main
        return build_and_run(cpp)

    def test_full_down_stick_converges_and_stops_at_110(self):
        driver = r"""
int main() {
	CVector pedPos(0.0f, 0.0f, 0.0f);
	CVector pedForward(0.0f, 1.0f, 0.0f);
	CVector pivot(0.0f, 0.0f, 0.6f);
	float range = 30.0f;
	CVector point = pedPos + pedForward*range;
	float prevYawRel = 0.0f;

	for(int i = 0; i < 400; i++)
		Update3DSFreeAimPointAngles(point, prevYawRel, pedPos, pedForward, pivot, range, 0.0f, -128.0f, 1.0f);

	CVector fromPed = point - pedPos;
	float mag = fromPed.Magnitude();
	float pitch = RADTODEG(Acos(Clamp(fromPed.z / mag, -1.0f, 1.0f)));
	assert(pitch > 108.0f && pitch < 112.0f);

	/* Further downward input must not push past the envelope. */
	CVector before = point;
	Update3DSFreeAimPointAngles(point, prevYawRel, pedPos, pedForward, pivot, range, 0.0f, -128.0f, 1.0f);
	fromPed = point - pedPos;
	pitch = RADTODEG(Acos(Clamp(fromPed.z / fromPed.Magnitude(), -1.0f, 1.0f)));
	assert(pitch <= 110.5f);

	printf("ok\n");
	return 0;
}
"""
        out = self._run_scenario(driver)
        self.assertEqual(out.strip(), "ok")

    def test_recovers_from_below_floor_with_hysteresis(self):
        driver = r"""
int main() {
	CVector pedPos(0.0f, 0.0f, 0.0f);
	CVector pedForward(0.0f, 1.0f, 0.0f);
	CVector pivot(0.0f, 0.0f, 0.6f);
	float range = 30.0f;
	/* Start the point straight down (180 degrees from vertical), well past
	 * the 110-degree floor -- simulates a state outside the envelope. */
	CVector point(0.0f, 0.001f, -range);
	float prevYawRel = 0.0f;

	CVector fromPed = point - pedPos;
	float startPitch = RADTODEG(Acos(Clamp(fromPed.z / fromPed.Magnitude(), -1.0f, 1.0f)));
	assert(startPitch > 110.0f);

	/* Stick up (positive stickY) must move the point back toward the band. */
	for(int i = 0; i < 2000; i++)
		Update3DSFreeAimPointAngles(point, prevYawRel, pedPos, pedForward, pivot, range, 0.0f, 128.0f, 1.0f);

	fromPed = point - pedPos;
	float pitch = RADTODEG(Acos(Clamp(fromPed.z / fromPed.Magnitude(), -1.0f, 1.0f)));
	assert(pitch < startPitch);
	assert(pitch <= 110.5f);

	printf("ok\n");
	return 0;
}
"""
        out = self._run_scenario(driver)
        self.assertEqual(out.strip(), "ok")

    def test_yaw_cone_stops_at_110_and_reenters_on_reverse(self):
        driver = r"""
int main() {
	CVector pedPos(0.0f, 0.0f, 0.0f);
	CVector pedForward(0.0f, 1.0f, 0.0f);
	CVector pivot(0.0f, 0.0f, 0.6f);
	float range = 30.0f;
	CVector point = pedPos + pedForward*range;
	float prevYawRel = 0.0f;

	for(int i = 0; i < 400; i++)
		Update3DSFreeAimPointAngles(point, prevYawRel, pedPos, pedForward, pivot, range, 128.0f, 0.0f, 1.0f);

	assert(Abs(RADTODEG(prevYawRel)) > 108.0f && Abs(RADTODEG(prevYawRel)) < 112.0f);
	float relBefore = prevYawRel;

	/* Further same-direction input must not push past the cone. */
	Update3DSFreeAimPointAngles(point, prevYawRel, pedPos, pedForward, pivot, range, 128.0f, 0.0f, 1.0f);
	assert(Abs(RADTODEG(prevYawRel)) <= 110.5f);

	/* Reverse input re-enters the cone (moves relative angle back down). */
	Update3DSFreeAimPointAngles(point, prevYawRel, pedPos, pedForward, pivot, range, -128.0f, 0.0f, 1.0f);
	assert(Abs(prevYawRel) < Abs(relBefore) + 1e-4f);

	printf("ok\n");
	return 0;
}
"""
        out = self._run_scenario(driver)
        self.assertEqual(out.strip(), "ok")

    def test_point_stays_at_range_from_pivot_after_accepted_yaw(self):
        driver = r"""
int main() {
	CVector pedPos(0.0f, 0.0f, 0.0f);
	CVector pedForward(0.0f, 1.0f, 0.0f);
	CVector pivot(0.0f, 0.0f, 0.6f);
	float range = 30.0f;
	CVector point = pedPos + pedForward*range;
	float prevYawRel = 0.0f;

	for(int i = 0; i < 50; i++){
		Update3DSFreeAimPointAngles(point, prevYawRel, pedPos, pedForward, pivot, range, 40.0f, 0.0f, 1.0f);
		CVector fromPivot = point - pivot;
		float dist = fromPivot.Magnitude();
		assert(dist > range - 0.01f && dist < range + 0.01f);
	}

	printf("ok\n");
	return 0;
}
"""
        out = self._run_scenario(driver)
        self.assertEqual(out.strip(), "ok")

    def test_zero_dt_is_a_noop(self):
        driver = r"""
int main() {
	CVector pedPos(0.0f, 0.0f, 0.0f);
	CVector pedForward(0.0f, 1.0f, 0.0f);
	CVector pivot(0.0f, 0.0f, 0.6f);
	float range = 30.0f;
	CVector point = pedPos + pedForward*range;
	float prevYawRel = 0.0f;
	CVector before = point;
	float prevBefore = prevYawRel;

	Update3DSFreeAimPointAngles(point, prevYawRel, pedPos, pedForward, pivot, range, 100.0f, -100.0f, 0.0f);

	assert(point.x == before.x && point.y == before.y && point.z == before.z);
	assert(prevYawRel == prevBefore);

	printf("ok\n");
	return 0;
}
"""
        out = self._run_scenario(driver)
        self.assertEqual(out.strip(), "ok")


if __name__ == "__main__":
    unittest.main()
