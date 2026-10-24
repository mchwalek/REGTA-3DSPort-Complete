#!/usr/bin/env python3
"""reLCS script-sound ids must match the PS2 LCS ids main.scm passes.

stories/src/audio/soundlist.h inherited Vice City's eScriptSounds order, so
PS2 ids 52/53 (Ammu-Nation door greeting) resolved to VC's BULLET_HIT_GROUND
and played a gunshot. This host-compiles the real header and checks the ids,
and checks ProcessOneShotScriptObject has a case for each new one-shot.
"""
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
SOUNDLIST = ROOT / 'stories/src/audio/soundlist.h'


def function(source, signature):
    start = source.index(signature)
    end = source.index('\n}', start) + 2
    return source[start:end]


def _enum_values(header, names):
    program = '#include <cstdio>\n#include "%s"\nint main() {\n' % header
    for name in names:
        program += '\tprintf("%s %%d\\n", (int)%s);\n' % (name, name)
    program += '\treturn 0;\n}\n'
    with tempfile.TemporaryDirectory() as tmp:
        src = Path(tmp) / 'enum.cpp'
        exe = Path(tmp) / 'enum'
        src.write_text(program)
        subprocess.run(['c++', '-std=c++11', '-o', str(exe), str(src)], check=True)
        out = subprocess.run([str(exe)], check=True, capture_output=True, text=True).stdout
    return {name: int(value) for name, value in (line.split() for line in out.splitlines())}


class TestScriptSoundIds(unittest.TestCase):
    def test_vc_ids_below_52_unchanged(self):
        values = _enum_values(SOUNDLIST, [
            'SCRIPT_SOUND_BANK_ALARM_LOOP',
            'SCRIPT_SOUND_PART_MISSION_COMPLETE',
            'SCRIPT_SOUND_WMYCW_TICKET_SPEECH',
            'SCRIPT_SOUND_NEW_BUILDING_INSECT_2',
            'SCRIPT_SOUND_NEW_WATERFALL',
        ])
        self.assertEqual(values, {
            'SCRIPT_SOUND_BANK_ALARM_LOOP': 0,
            'SCRIPT_SOUND_PART_MISSION_COMPLETE': 1,
            'SCRIPT_SOUND_WMYCW_TICKET_SPEECH': 15,
            'SCRIPT_SOUND_NEW_BUILDING_INSECT_2': 50,
            'SCRIPT_SOUND_NEW_WATERFALL': 51,
        })

    def test_lcs_ids_match_ps2(self):
        expected = {
            'SCRIPT_SOUND_AMMUNATION_WELCOME_1': 52,
            'SCRIPT_SOUND_AMMUNATION_WELCOME_2': 53,
            'SCRIPT_SOUND_AMMUNATION_WELCOME_3': 54,
            'SCRIPT_SOUND_C_OR_D_1': 55,
            'SCRIPT_SOUND_C_OR_D_7': 61,
            'SCRIPT_SOUND_DOCK_BA': 62,
            'SCRIPT_SOUND_DOCK_BB': 63,
            'SCRIPT_SOUND_PIZZA_THROW': 66,
            'SCRIPT_SOUND_GATE_START': 68,
            'SCRIPT_SOUND_GATE_STOP': 69,
            'SCRIPT_SOUND_FRONTEND_ENTER': 70,
            'SCRIPT_SOUND_FRONTEND_BEEP': 71,
            'SCRIPT_SOUND_BULLET_HIT_GROUND_1': 72,
            'SCRIPT_SOUND_GUNSHELL_DROP_SOFT': 87,
            'SCRIPT_SOUND_TOTAL': 88,
        }
        self.assertEqual(_enum_values(SOUNDLIST, list(expected)), expected)

    def test_one_shot_cases_present(self):
        source = (ROOT / 'stories/src/audio/AudioLogic.cpp').read_text()
        body = function(source, 'cAudioManager::ProcessOneShotScriptObject')
        for token in ('case SCRIPT_SOUND_AMMUNATION_WELCOME_1', 'SFX_AMMU_AA', 'SFX_DOCK_BB',
                      'SFX_PIZZA_THROW', 'SFX_GATE_START_CLU', 'SFX_GATE_STOP_CLU'):
            self.assertIn(token, body)


if __name__ == '__main__':
    unittest.main()
