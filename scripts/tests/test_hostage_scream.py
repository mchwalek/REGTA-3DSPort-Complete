#!/usr/bin/env python3
"""Regression test: a ped held hostage in the player's car screams once, and
never in a taxi/cabbie/ambulance (PS2 0x1d6f30 / 0x32a5e0). The Taxi Driver
fare is scripted as hostage (SET_CHAR_FRIGHTENED_IN_JACKED_CAR) and screamed
on every drop-off."""
import unittest

from cpptest import between, compile_and_run, harness, read_source


class TestHostageScream(unittest.TestCase):
    def test_scream_once_and_not_in_taxi(self):
        src = read_source("stories/src/peds/Ped.cpp")
        block = between(src, "if (bHeldHostageInCar) {", "if (m_delayedSoundID >= 0")
        compile_and_run(harness("hostage_scream.cpp", BLOCK=block))


if __name__ == "__main__":
    unittest.main()
