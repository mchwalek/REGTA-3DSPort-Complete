#!/usr/bin/env python3
"""Regression test: AI peds with non-fist melee weapons must be able to swing
at the player (docs/superpowers/specs/2026-10-17-ai-melee-attack-gate-design.md).

PS2 VA 0x31e51c has no reachability check before SetAttack(m_pedInObjective).
VC's canReachVictim gate left cops standing ~2m away with a nightstick.

PS2 also never seeks VC's hexagon melee attack points (FindMeleeAttackPoint):
with LCS's unarmed range they sit ~5m from the player, so unarmed peds walked
out to them, shuffled back, and looped forever.
"""
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PEDAI_CPP = ROOT / "stories" / "src" / "peds" / "PedAI.cpp"


class TestAiMeleeAttackGate(unittest.TestCase):
    def setUp(self):
        source = PEDAI_CPP.read_text()
        start = source.index("CPed::KillCharOnFootMelee(")
        self.body = source[start:source.index("\n}\n", start)]

    def test_attack_has_no_reachability_gate(self):
        self.assertIn("\n\t\tSetAttack(m_pedInObjective);", self.body)
        self.assertNotIn("canReachVictim", self.body)

    def test_fists_do_not_seek_hexagon_attack_points(self):
        self.assertNotIn("->FindMeleeAttackPoint(", self.body)
        self.assertNotIn("->GetMeleeAttackCoords(", self.body)


if __name__ == "__main__":
    unittest.main()
