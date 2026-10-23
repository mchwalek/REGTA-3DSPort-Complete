#!/usr/bin/env python3
"""Regression test: the running punch (ANIM_MELEE_ATTACK_START via
SetAttack(nil)) must play through to its fire frame.

reLCS inherited a Vice City block in CPed::Attack that cleared ASSOC_RUNNING
at animLoopStart (t=0.1) while the player kept moving, so the fire frame
(t=0.2) never ran and the punch whiffed. PS2 CPed::Attack (SLES_541.35
0x1bc498) has no such block and never reads m_fMoveSpeed.
"""
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PEDFIGHT_CPP = ROOT / "stories" / "src" / "peds" / "PedFight.cpp"


class TestRunningPunchNoPause(unittest.TestCase):
    def test_attack_does_not_pause_melee_start_anim(self):
        source = PEDFIGHT_CPP.read_text()
        start = source.index("\nCPed::Attack(void)")
        body = source[start:source.index("\n}\n", start)]
        self.assertNotIn("m_fMoveSpeed", body)
        self.assertNotIn("meleeAttackStarted && IsPlayer()", body)

    def test_unarmed_start_anim_fires_before_its_last_frame(self):
        # FIGHTppunch (ANIM_MELEE_ATTACK_START, unarmed) is 0.2333 s; the anim
        # finishing clears the attack in UpdateAnim before Attack() runs, so the
        # fire delay must leave more than one 30 fps frame before the end.
        source = PEDFIGHT_CPP.read_text()
        start = source.index("\nCPed::Attack(void)")
        body = source[start:source.index("\n}\n", start)]
        self.assertIn("m_AnimToPlay == ASSOCGRP_UNARMED)\n\t\t\t\t\t\t\tdelayBetweenAnimAndFire = 0.15f;", body)


if __name__ == "__main__":
    unittest.main()
