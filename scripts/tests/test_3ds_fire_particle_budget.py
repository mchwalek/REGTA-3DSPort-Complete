#!/usr/bin/env python3
"""Regression test: smoke/explosions must not starve fire particles on 3DS.

The 3DS capped every particle at 256 (128 in stereo), PS2 has 750. After the
Trouble with Triads warehouse blast and while ballots burn in Friggin' the
Riggin', smoke filled the cap and fire/flamethrower flames were refused, so
fires vanished. Fire types now have their own budget (the rest of the PS2 pool).

Extracts the RW_3DS pool defines and the _3DS budget helpers from
stories/src/renderer/Particle.cpp into cpp/fire_particle_budget.cpp.
"""
import unittest

from cpptest import Program, between, harness, read_source


class TestFireParticleBudget(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        src = read_source("stories/src/renderer/Particle.cpp")
        defines = between(src, "#define MAX_PARTICLES_ON_SCREEN   (750)\n#define MAX_EFFECT", "\n#else")
        budget = between(src, "static int nActiveParticles3DS;", "\n#endif\n\nint32 Randomizer;")
        cls.program = Program(harness("fire_particle_budget.cpp", DEFINES=defines, BUDGET=budget))

    @classmethod
    def tearDownClass(cls):
        cls.program.close()

    def _scenario(self, name):
        self.assertEqual(self.program.run(name).strip(), "ok")

    def test_smoke_does_not_starve_fire(self):
        self._scenario("smoke_does_not_starve_fire")

    def test_fire_shares_rest_of_ps2_pool(self):
        self._scenario("fire_shares_rest_of_ps2_pool")

    def test_stereo_halves_both_budgets(self):
        self._scenario("stereo_halves_both_budgets")


if __name__ == "__main__":
    unittest.main()
