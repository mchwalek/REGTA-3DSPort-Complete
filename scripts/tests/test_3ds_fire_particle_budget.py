#!/usr/bin/env python3
"""Regression test: smoke must not starve fire particles on 3DS.

The 3DS caps particles at 256 (128 in stereo), PS2 has 750. After the
Trouble with Triads warehouse blast and while ballots burn in Friggin' the
Riggin', smoke filled the cap and fire/flamethrower flames were refused, so
fires vanished. A fire particle now replaces the oldest smoke particle when
the cap is full, and a flamethrower particle may also replace the oldest fire
flame; the cap itself stays (raising it cost frame rate).

Extracts the RW_3DS pool define and the _3DS admission helpers from
stories/src/renderer/Particle.cpp into cpp/fire_particle_budget.cpp.
"""
import unittest

from cpptest import Program, between, harness, read_source


class TestFireParticleBudget(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        src = read_source("stories/src/renderer/Particle.cpp")
        defines = between(src, "#define MAX_PARTICLES_ON_SCREEN   (256)", "\n#else")
        budget = between(src, "static int nActiveParticles3DS;", "\n#endif\n\nint32 Randomizer;")
        cls.program = Program(harness("fire_particle_budget.cpp", DEFINES=defines, BUDGET=budget))

    @classmethod
    def tearDownClass(cls):
        cls.program.close()

    def _scenario(self, name):
        self.assertEqual(self.program.run(name).strip(), "ok")

    def test_fire_replaces_oldest_smoke(self):
        self._scenario("fire_replaces_oldest_smoke")

    def test_fire_falls_back_to_other_smoke(self):
        self._scenario("fire_falls_back_to_other_smoke")

    def test_fire_refused_when_no_smoke(self):
        self._scenario("fire_refused_when_no_smoke")

    def test_flamethrower_replaces_oldest_flame(self):
        self._scenario("flamethrower_replaces_oldest_flame")

    def test_stereo_halves_cap(self):
        self._scenario("stereo_halves_cap")


if __name__ == "__main__":
    unittest.main()
