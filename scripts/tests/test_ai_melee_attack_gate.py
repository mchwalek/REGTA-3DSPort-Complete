#!/usr/bin/env python3
"""Regression test: AI peds with non-fist melee weapons must be able to swing
at the player (docs/superpowers/specs/2026-10-17-ai-melee-attack-gate-design.md).

PS2 VA 0x31e51c has no reachability check before SetAttack(m_pedInObjective).
VC's canReachVictim gate left cops standing ~2m away with a nightstick.

PS2 also never seeks VC's hexagon melee attack points (FindMeleeAttackPoint):
with LCS's unarmed range they sit ~5m from the player, so unarmed peds walked
out to them, shuffled back, and looped forever. For fists within 5m of the
player PS2 gates on a distance of 0, so they attack instead of seeking forever.
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

    def test_fists_near_player_gate_on_zero_distance(self):
        # PS2 0x31e0cc: dist starts at 0; seeking to 0.3m through ped collision never finishes.
        self.assertIn("float dist = 0.0f;", self.body)
        self.assertEqual(self.body.count("dist = distWithTargetSc;"), 3)
        self.assertIn("if (dist > maxDistToKeep", self.body)
        self.assertIn("&& dist < wepRange", self.body)


if __name__ == "__main__":
    unittest.main()
