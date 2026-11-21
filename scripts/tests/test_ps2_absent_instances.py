#!/usr/bin/env python3
"""Regression test: IPL instances that PS2 never places must not be loaded.

The Shoreside Vale northern tunnel has three light-volume meshes in the
SD card's suburb.ipl (Trans_lights01-03). PS2's SUBURB.LVZ has no instance
of them; on 3DS they drew as grey slabs between the tunnel walls.

Extracts the real IsInstanceAbsentOnPS2 from FileLoader.cpp and the real
CGeneral::faststricmp from General.h and compiles them into
cpp/ps2_absent_instances.cpp.
"""
import unittest

from cpptest import between, compile_and_run, extract_function, harness, read_source


class TestPS2AbsentInstances(unittest.TestCase):
    def test_only_tunnel_light_volumes_are_dropped(self):
        func = between(read_source("stories/src/core/FileLoader.cpp"),
                       "static const char *const ps2AbsentInstanceModels[]",
                       "\n#endif\n\nvoid\nCFileLoader::LoadObjectInstance")
        stricmp = between(read_source("stories/src/core/General.h"),
                          "static bool faststricmp", "\n\n\tstatic bool SolveQuadratic")
        compile_and_run(harness("ps2_absent_instances.cpp", FUNCTION=func, FASTSTRICMP=stricmp))

    def test_load_object_instance_skips_absent_models(self):
        func = extract_function(read_source("stories/src/core/FileLoader.cpp"),
                                "void\nCFileLoader::LoadObjectInstance(const char *line)")
        self.assertIn("IsInstanceAbsentOnPS2(", func)
        self.assertLess(func.index("IsInstanceAbsentOnPS2("), func.index("RwMatrixCreate()"))


if __name__ == "__main__":
    unittest.main()
