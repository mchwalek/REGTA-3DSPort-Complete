#!/usr/bin/env python3
"""Regression test: a ped on foot with OBJECTIVE_WAIT_IN_CAR (restored after
LEAVE_CAR) must drop the objective, not become PED_DRIVING (PS2 0x309db0).
Otherwise he is never rendered: Massimo vanished after leaving the heli in
"Calm Before the Storm"."""
import unittest

from cpptest import between, compile_and_run, harness, read_source


class TestWaitInCarObjective(unittest.TestCase):
    def test_on_foot_ped_drops_wait_in_car(self):
        src = read_source("stories/src/peds/PedAI.cpp")
        src = src[src.index("CPed::ProcessObjective(void)"):]
        case = between(src, "case OBJECTIVE_WAIT_IN_CAR:", "case OBJECTIVE_WAIT_IN_CAR_THEN_GET_OUT:")
        compile_and_run(harness("wait_in_car_objective.cpp", CASE=case))


if __name__ == "__main__":
    unittest.main()
