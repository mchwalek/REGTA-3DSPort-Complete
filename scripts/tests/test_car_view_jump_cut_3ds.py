#!/usr/bin/env python3
"""Regression test: 3DS car view changes into/out of bumper or cinematic cut.

PS2 CamControl (0x288798) jump-cuts ReqMode MODE_1STPERSON and the Obbe
cinematic camera (TakeControl 0x294aa0 / RestoreWithJumpCut 0x292d98 with
JUMP_CUT); only zoom 1-3 changes use StartTransition. The 3DS preset blend in
CCamera::Process must not glide, pull in or fade the car on those changes.
"""
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CAMERA_CPP = ROOT / "stories" / "src" / "core" / "Camera.cpp"


class TestCarViewJumpCut3ds(unittest.TestCase):
    def test_special_car_view_change_skips_blend(self):
        source = CAMERA_CPP.read_text()
        snap = source.index("const bool snapPreset3DS=")
        condition = source[snap:source.index(";", snap)]
        for term in ("vehicleView3DS", "!exitPreset3DS", "specialView3DS", "presetKey3DS!=presetTransition3DS.key"):
            self.assertIn(term, condition)
        reset = source.index("if(snapPreset3DS){presetTransition3DS.Reset();", snap)
        self.assertLess(reset, source.index("presetTransition3DS.Apply(", snap))
        self.assertIn("|| cinema3DS || snapPreset3DS)\n\t\tentryDistance3DS.active=false;", source)
        self.assertIn("!snapPreset3DS && wasPresetActive3DS", source)
        self.assertIn("if(snapOpacity3DS)visibleOpacity3DS.value=desiredOpacity3DS;", source)


if __name__ == "__main__":
    unittest.main()
