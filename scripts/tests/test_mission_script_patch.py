#!/usr/bin/env python3
"""Calm Before the Storm (JDT7): skipping the heli-landing cutscene at its first
wait skipped the landing order, so the mission failed with "You've blown your
cover!". PatchCalmBeforeTheStormSkip moves the landing GOSUB before the wait.

Set LCS_MAIN_SCM to the SD card's DATA/MAIN.SCM to also check the real file."""
import os
import tempfile
import unittest
from pathlib import Path

from cpptest import Program, extract_function, harness, read_source

WAIT = bytes.fromhex('ae05 010041 06 67790000 08 8813')  # CALL 31079 5000
IF_FALSE_NEXT = bytes.fromhex('4d00 06 7ee9ffff')
GOTO_SKIP = bytes.fromhex('0200 06 7fe8ffff')
GOSUB_LAND = bytes.fromhex('5000 06 18dfffff')
IF_FALSE_PAST = bytes.fromhex('4d00 06 77e9ffff')
ORIGINAL = WAIT + IF_FALSE_NEXT + GOTO_SKIP + GOSUB_LAND
PATCHED = GOSUB_LAND + WAIT + IF_FALSE_PAST + GOTO_SKIP

# Script-space offsets in the EUR main.scm: JDT7 base and the patched block.
MISSION_BASE, BLOCK = 0xb949e, 0xbab05


class MissionScriptPatch(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fn = extract_function(read_source('stories/src/control/Script5.cpp'),
                              'static bool PatchCalmBeforeTheStormSkip')
        cls.program = Program(harness('mission_script_patch.cpp', FUNCTION=fn))

    @classmethod
    def tearDownClass(cls):
        cls.program.close()

    def _patch(self, data):
        with tempfile.TemporaryDirectory() as tmp:
            src, dst = Path(tmp) / 'in', Path(tmp) / 'out'
            src.write_bytes(data)
            patched = self.program.run(str(src), str(dst)).strip() == '1'
            return patched, dst.read_bytes()

    def test_jump_targets(self):
        # Mission-local GOTO targets are stored negated.
        def target(insn):
            return -int.from_bytes(insn[3:7], 'little', signed=True)
        self.assertEqual(target(IF_FALSE_NEXT), BLOCK + len(WAIT) + len(IF_FALSE_NEXT) + len(GOTO_SKIP) - MISSION_BASE)
        self.assertEqual(target(IF_FALSE_PAST), BLOCK + len(ORIGINAL) - MISSION_BASE)

    def test_reorders_block_and_leaves_the_rest(self):
        head, tail = b'\x01\x02\x03', b'\x1d\x81\xdb\x5e'
        patched, out = self._patch(head + ORIGINAL + tail)
        self.assertTrue(patched)
        self.assertEqual(out, head + PATCHED + tail)

    def test_noop_without_pattern_and_idempotent(self):
        for data in (b'', ORIGINAL[:-1], PATCHED):
            patched, out = self._patch(data)
            self.assertFalse(patched)
            self.assertEqual(out, data)

    def test_real_main_scm(self):
        path = os.environ.get('LCS_MAIN_SCM')
        if not path or not os.path.exists(path):
            self.skipTest('LCS_MAIN_SCM not set')
        data = Path(path).read_bytes()
        self.assertEqual(data.count(ORIGINAL), 1)
        raw = BLOCK + 8  # 8-byte file header precedes script space
        self.assertEqual(data[raw:raw + len(ORIGINAL)], ORIGINAL)
        patched, out = self._patch(data)
        self.assertTrue(patched)
        self.assertEqual(out[raw:raw + len(PATCHED)], PATCHED)
        self.assertEqual(out[:raw] + out[raw + len(PATCHED):], data[:raw] + data[raw + len(ORIGINAL):])


if __name__ == '__main__':
    unittest.main()
