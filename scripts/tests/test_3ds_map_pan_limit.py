#!/usr/bin/env python3
"""Regression test for the 3DS pause-menu map panning (PS2 LCS behaviour,
SLES_541.35 0x33f578): the map scrolls under a centred crosshair until its
edge (the 320x220 atlas, see CMenuManager::PrintMap) meets the screen edge,
then the crosshair itself moves. Moving back snaps the crosshair to the
centre before the map scrolls again.

Extracts the real MAP_PAN_LIMIT_X/_Y macros and screen<->world helpers from
Frontend.cpp, includes common/3ds/MapPan3DS.h, compiles them into
cpp/map_pan_limit.cpp and checks that:
- every atlas corner is reachable by the crosshair at min and max zoom,
- the crosshair stays centred while the map can still scroll,
- moving back snaps the crosshair to the centre,
- MapScreenToWorld3DS and MapWorldToScreen3DS are inverses.
"""
import unittest

from cpptest import between, compile_and_run, harness, read_source


class Test3DSMapPanLimit(unittest.TestCase):
    def test_ps2_map_pan(self):
        frontend = read_source("stories/src/core/Frontend.cpp")
        macros = between(frontend, "#define MAP_PAN_LIMIT_X(s) Max", "#define CAN_PAN_X_AT_CURRENT_ZOOM")
        helpers = between(frontend, "static CVector2D\nMapScreenToWorld3DS", "#endif\n\n#ifdef CUTSCENE_BORDERS_SWITCH")
        registration = "".join(line + "\n" for line in read_source("stories/src/core/Radar.h").splitlines()
                               if line.startswith("#define LCS_MENU_MAP_"))
        compile_and_run(harness("map_pan_limit.cpp", REGISTRATION=registration, MACROS=macros, HELPERS=helpers))


if __name__ == "__main__":
    unittest.main()
