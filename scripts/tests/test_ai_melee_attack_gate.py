#!/usr/bin/env python3
"""Regression test: AI peds with non-fist melee weapons must be able to swing
at the player (docs/superpowers/specs/2026-10-17-ai-melee-attack-gate-design.md).

CPed::KillCharOnFootMelee's non-fist approach branch never sets canReachVictim,
so the attack gate guarding SetAttack(m_pedInObjective) must also pass for
!isUnarmedOrBrassKnuckle (PS2 VA 0x31e51c has no reachability check at all).
Without it, cops stand ~2m from the player with a nightstick and never swing.
"""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PEDAI_CPP = ROOT / "stories" / "src" / "peds" / "PedAI.cpp"


class TestAiMeleeAttackGate(unittest.TestCase):
    def test_attack_gate_passes_for_non_fist_melee(self):
        source = PEDAI_CPP.read_text()
        start = source.index("CPed::KillCharOnFootMelee(")
        body = source[start:source.index("\n}\n", start)]
        attack = body.index("SetAttack(m_pedInObjective);")
        gate = re.findall(r"if \((.*)\) \{", body[:attack])[-1]
        self.assertIn("canReachVictim", gate)
        self.assertIn("!isUnarmedOrBrassKnuckle", gate)


if __name__ == "__main__":
    unittest.main()
