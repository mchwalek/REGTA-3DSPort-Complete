#!/usr/bin/env python3
"""Regression test for the 3DS third-person free-aim latch (CPad::Update3DSFreeAim).

Extracts the real function bodies from stories/src/core/Pad.cpp, compiles them
into cpp/free_aim_latch.cpp (a minimal CPad stub), and asserts the latch's
enter/exit state machine:
  1. tap L while targeting -> latches
  2. releasing target -> unlatches, restores bFreeCam
  3. entering a vehicle -> unlatches
  4. player ped gone -> unlatches
  5. holding L with no fresh press-edge -> does not re-latch
  6. CCamera::bFreeCam save/restore is correct when the user's Free Cam
     option was already on before latching
  7. CURMODE 3 (Target remapped onto L) never latches, even with a fresh
     L press-edge and GetTarget() true
  8. the entry frame is flagged via Is3DSFreeAimEnteredThisFrame(), and only
     that frame; unlatching snaps the camera behind the player
  9. the PS2 weapon gate (Can3DSFreeAim) refuses entry and ends free aim
     when it fails; entry seeds the aim point via Begin3DSFreeAim
"""
import unittest

from cpptest import compile_and_run, extract_function, harness, read_source


def member(source, ret, name):
    """Extract `ret\\nCPad::name()` and rename it to an in-class definition."""
    signature = f"{ret}\nCPad::{name}()"
    return extract_function(source, signature).replace(signature, f"{ret} {name}()")


class Test3DSFreeAimLatch(unittest.TestCase):
    def test_latch_state_machine(self):
        source = read_source("stories/src/core/Pad.cpp")
        functions = "\n".join([
            member(source, "void", "Update3DSFreeAim"),
            member(source, "bool", "Is3DSFreeAimActive"),
            member(source, "bool", "Is3DSFreeAimEnteredThisFrame"),
        ])
        out = compile_and_run(harness("free_aim_latch.cpp", FUNCTIONS=functions))
        self.assertEqual(out.strip(), "ok")


if __name__ == "__main__":
    unittest.main()
