#!/usr/bin/env python3
"""Compile the real debug-menu mission-batch stepping (L/R) against host stubs."""
import unittest

from cpptest import between, compile_and_run, extract_function, harness, read_source


class MissionSwitcherBatches(unittest.TestCase):
    def test_batch_stepping(self):
        source = read_source('stories/src/core/re3.cpp')
        fns = '\n'.join(extract_function(source, sig) for sig in (
            'static bool\nSameMissionBatch(',
            'static int32\nMissionBatchStart(',
            'static int32\nStepMissionBatch('))
        missions = between(source, 'static const char* missions[] = {', '};', include_end=True)
        compile_and_run(harness('mission_switcher_batches.cpp', FUNCTIONS=fns, MISSIONS=missions), sanitize=False)


if __name__ == '__main__':
    unittest.main()
