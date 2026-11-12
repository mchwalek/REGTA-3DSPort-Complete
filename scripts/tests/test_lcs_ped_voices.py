#!/usr/bin/env python3
"""reLCS civilian/gang ped voices must stay inside their own sample blocks.

GetPedCommentSfx had every LCS civilian model mapping commented out, so only
MI_MALE01 talked and every other ped (women too) got the generic male lines.
The voice tables were decoded from PS2 GetPedCommentSfx (SLES_541.35
0x1a88d0, model jump table 0x3af170). A row's count picks a random sample
from base..base+count-1, so a too-large count plays another voice's line.
"""
import re
import unittest

from cpptest import extract_function, read_source

ROW = re.compile(r'\{ (SOUND_\w+), (SFX_\w+|NO_SAMPLE), (\d+) \}')
TABLE = re.compile(r'static const tPedVoiceLine (\w+)\[\] = \{(.*?)\n\};', re.S)


def _tables():
    source = read_source('stories/src/audio/AudioLogic.cpp')
    return {name: ROW.findall(body) for name, body in TABLE.findall(source)}


def _samples():
    header = read_source('stories/src/audio/AudioSamples.h')
    return [m.group(1) for m in re.finditer(r'^\s*(SFX_\w+)\s*[,=]', header, re.M)]


class TestPedVoices(unittest.TestCase):
    def test_rows_stay_in_their_sample_block(self):
        samples = _samples()
        index = {name: i for i, name in enumerate(samples)}
        tables = _tables()
        self.assertEqual(len(tables), 74)
        for table, rows in tables.items():
            for sound, sample, count in rows:
                if sample == 'NO_SAMPLE':
                    continue
                m = re.fullmatch(r'(\w+_)0?1', sample)
                self.assertIsNotNone(m, (table, sample))
                # names can skip a number (SFX_CONST1_CHAT_1, _3, _4), so check the block prefix only
                for k in range(int(count)):
                    name = samples[index[sample] + k]
                    self.assertRegex(name, '^%s\\d+$' % m.group(1), (table, sound, count))

    def test_ps2_decoded_rows(self):
        tables = _tables()
        self.assertIn(('SOUND_PED_CHAT', 'SFX_MALE03_CHAT_1', '3'), tables['aMale03Voice'])
        self.assertIn(('SOUND_PED_SOLICIT', 'SFX_PROSTITUTE2_SPECIAL_CASE_1', '3'), tables['aProstituteVoice'])
        self.assertIn(('SOUND_PED_ATTACK', 'SFX_FEMALE02_FIGHT_1', '2'), tables['aFemale02Voice'])
        for rows in tables.values():
            self.assertEqual(rows[-1], ('SOUND_TOTAL_SOUNDS', 'NO_SAMPLE', '0'))

    def test_models_wired(self):
        body = extract_function(read_source('stories/src/audio/AudioLogic.cpp'), 'cAudioManager::GetPedCommentSfx')
        self.assertNotIn('LCS: removed for now', body)
        for table in _tables():
            self.assertIn(', %s, ' % table, body)
        self.assertIn('case MI_FEMALE01: return GetVoiceTalkSfx(ped, sound, aFemale01Voice, TRUE);', body)
        self.assertIn('case MI_GANG01: return GetVoiceTalkSfx(ped, sound, aGang01Voice, FALSE);', body)
        self.assertIn('case MI_MALE01: return GetDefaultTalkSfx(ped, sound);', body)


if __name__ == '__main__':
    unittest.main()
