#!/usr/bin/env python3
"""Regression test: 3DS melee must stay in the on-foot follow cam
(docs/superpowers/specs/2026-10-17-ps2-melee-camera-design.md).

PS2 CCamera::CamControl never stores MODE_FIGHT_CAM (36) to ReqMode
(0x3d9bca), so melee stays in the follow cam. reLCS's inherited
Process_Fight_Cam swings the camera on every strike, so every fight-cam
request in CamControl must be compiled out on _3DS (kept for non-_3DS).
"""
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CAMERA_CPP = ROOT / "stories" / "src" / "core" / "Camera.cpp"


class TestNoFightCamOn3ds(unittest.TestCase):
    def test_fight_cam_request_is_not_3ds(self):
        source = CAMERA_CPP.read_text()
        start = source.index("CCamera::CamControl(")
        lines = source[start:source.index("\n}\n", start)].splitlines()
        requests = [i for i, line in enumerate(lines) if "ReqMode = CCam::MODE_FIGHT_CAM;" in line]
        self.assertTrue(requests)
        for i in requests:
            conditional = next(l.strip() for l in reversed(lines[:i]) if l.strip().startswith(("#if", "#else", "#endif")))
            self.assertEqual(conditional, "#ifndef _3DS")


if __name__ == "__main__":
    unittest.main()
