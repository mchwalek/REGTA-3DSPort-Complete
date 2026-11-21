#!/usr/bin/env python3
"""Regression test for the end credits tune being dropped
(cMusicManager in stories/src/audio/MusicManager.cpp).

SALH5 asks for game mode (SWITCH_CAR_RADIO 1) and, on some camera shots, a
frame later for frontend mode plus FINALE (PLAY_END_OF_GAME_TUNE). The
switch to game mode was already latched, and its completion cleared the
FINALE request, so the credits ran in silence. The harness runs the real
service code against a fake stream.
"""
import unittest

from cpptest import Program, extract_function, harness, read_source


class TestMusicFrontendTrackRace(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        src = read_source("stories/src/audio/MusicManager.cpp")
        header = read_source("stories/src/audio/MusicManager.h").replace('#include "audio_enums.h"', "")
        functions = "".join(extract_function(src, sig) for sig in (
            "void\ncMusicManager::ChangeMusicMode(",
            "void\ncMusicManager::Service()",
            "void\ncMusicManager::ServiceFrontEndMode()",
            "void\ncMusicManager::PlayFrontEndTrack(",
        ))
        cls.program = Program(harness(
            "music_frontend_track_race.cpp",
            ENUMS=read_source("stories/src/audio/audio_enums.h").replace("#pragma once", ""),
            HEADER=header,
            FUNCTIONS=functions,
        ))

    @classmethod
    def tearDownClass(cls):
        cls.program.close()

    def _scenario(self, name):
        self.assertEqual(self.program.run(name).strip(), "ok")

    def test_finale_survives_reverted_switch_to_game(self):
        self._scenario("finale_survives_reverted_switch_to_game")

    def test_same_frame_switch_plays_finale(self):
        self._scenario("same_frame_switch_plays_finale")

    def test_finale_after_jingle_end_switch(self):
        self._scenario("finale_after_jingle_end_switch")

    def test_unreversed_switch_to_game_clears_track(self):
        self._scenario("unreversed_switch_to_game_clears_track")


if __name__ == "__main__":
    unittest.main()
