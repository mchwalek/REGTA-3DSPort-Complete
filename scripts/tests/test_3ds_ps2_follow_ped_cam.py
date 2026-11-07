"""Host-compiled tests for the PS2-ported MODE_FOLLOWPED pure-math helpers
in stories/src/core/Cam.cpp (CCam::Process_FollowPed_Rotation). Each helper
is extracted verbatim from the real source file and compiled into
cpp/ps2_follow_ped_cam.cpp, so these tests exercise the exact code that ships
on-device, not a reimplementation. See
docs/superpowers/specs/2026-10-16-ps2-on-foot-camera-design.md for the
derivation of every constant asserted below.
"""
import unittest

from cpptest import Program, extract_function, harness, read_source

HELPERS = [
    "LookDown", "StringDist", "PitchStep", "StickTarget",
    "SpeedStep", "AutoRotateStep", "LevelPitch",
]


class TestPS2FollowPedHelpers(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        source = read_source("stories/src/core/Cam.cpp")
        functions = "\n".join(extract_function(source, f"float\nPS2FollowPed{name}(") for name in HELPERS)
        cls.program = Program(harness("ps2_follow_ped_cam.cpp", FUNCTIONS=functions))

    @classmethod
    def tearDownClass(cls):
        cls.program.close()

    def _scenario(self, name):
        self.assertEqual(self.program.run(name).strip(), "ok")

    def test_look_down_per_zoom(self):
        self._scenario("look_down_per_zoom")

    def test_string_dist_follows_zoom(self):
        self._scenario("string_dist_follows_zoom")

    def test_pitch_step_converges_and_respects_cap(self):
        self._scenario("pitch_step_converges_and_respects_cap")

    def test_stick_target_is_quadratic_and_signed(self):
        self._scenario("stick_target_is_quadratic_and_signed")

    def test_speed_step_smooths_clamps_and_snaps(self):
        self._scenario("speed_step_smooths_clamps_and_snaps")

    def test_auto_rotate_step_caps_and_thresholds(self):
        self._scenario("auto_rotate_step_caps_and_thresholds")

    def test_level_pitch_eases_toward_level(self):
        self._scenario("level_pitch_eases_toward_level")


if __name__ == "__main__":
    unittest.main()
