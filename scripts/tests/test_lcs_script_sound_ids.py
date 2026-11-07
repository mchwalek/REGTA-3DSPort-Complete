#!/usr/bin/env python3
"""reLCS script-sound ids must match the PS2 LCS ids main.scm passes.

stories/src/audio/soundlist.h inherited Vice City's eScriptSounds order, so
PS2 ids 52/53 (Ammu-Nation door greeting) resolved to VC's BULLET_HIT_GROUND
and played a gunshot. This host-compiles the real header and checks the ids,
and checks ProcessOneShotScriptObject has a case for each new one-shot.
"""
import re
import unittest

from cpptest import ROOT, between, compile_and_run, extract_function, harness, read_source

SOUNDLIST = ROOT / 'stories/src/audio/soundlist.h'
PS2_ONE_SHOT_PRIORITY = [3,3,3,3,3,3,3,3,3,3,3,3,3,5,4,2,5,5,3,5,2,2,1,1,3,1,3,3,1,1,1,0,4,4,4,3,1,1,1,1,1,1,1,1,1,1,1,1,1,6,1,1,1,1,0,1,3,4,2,0,0,6,6,0,0,0,0,0,0,0,0,0,0,0,1,2,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,1,0,0,0,3,1,1,1,9,0,0,0,1,2,2,0,0,2,3,3,3,5,1,1,1,1,1,2,2,1,2,2,2,2,2,2,2,2,3,4,7,1,4,3,4,2,2,2,3,1,2,1,3,5,3,4,6,4,6,3,0,0,0,0,0,0,3,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,1,1,1,1,3,1,1,2,1,1,0,0,0,0,0,3,3,1,1,1,0,0,0]


def _enum_values(header, names):
    prints = ''.join('\tprintf("%s %%d\\n", (int)%s);\n' % (name, name) for name in names)
    out = compile_and_run(harness('enum_values.cpp', HEADER=str(header), PRINTS=prints), sanitize=False)
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
        source = read_source('stories/src/audio/AudioLogic.cpp')
        body = extract_function(source, 'cAudioManager::ProcessOneShotScriptObject')
        for token in ('case SCRIPT_SOUND_AMMUNATION_WELCOME_1', 'SFX_AMMU_AA', 'SFX_DOCK_BB',
                      'SFX_PIZZA_THROW', 'SFX_GATE_START_CLU', 'SFX_GATE_STOP_CLU'):
            self.assertIn(token, body)

    def test_esound_extended(self):
        expected = {
            'SOUND_SET_203': 203,
            'SOUND_PED_CRUNCH': 204,
            'SOUND_FRONTEND_BEEP': 205,
            'SOUND_PED_CARJACKED_WHOOSH': 206,
            'SOUND_SET_207': 207,
            'SOUND_TOTAL_SOUNDS': 208,
        }
        values = _enum_values(SOUNDLIST, list(expected) + ['SOUND_NO_SOUND'])
        self.assertEqual({name: values[name] for name in expected}, expected)
        self.assertGreaterEqual(values['SOUND_NO_SOUND'], values['SOUND_TOTAL_SOUNDS'])

    def test_priority_table_matches_ps2(self):
        source = read_source('stories/src/audio/AudioManager.cpp')
        table = between(source, 'static Const uint8 OneShotPriority[] = {', '};')
        values = [int(v) for v in re.findall(r'\d+', table.split('=', 1)[1])]
        self.assertEqual(values, PS2_ONE_SHOT_PRIORITY)

    def test_frontend_beep_wired(self):
        audio = read_source('stories/src/audio/AudioLogic.cpp')
        body = extract_function(audio, 'cAudioManager::ProcessFrontEnd()')
        self.assertIn('case SOUND_FRONTEND_BEEP', body)
        self.assertIn('SFX_BEEP', body)

        script = read_source('stories/src/control/Script2.cpp')
        for token in ('case SCRIPT_SOUND_FRONTEND_ENTER', 'PlayFrontEndSound(SOUND_FRONTEND_ENTER_OR_ADJUST',
                      'case SCRIPT_SOUND_FRONTEND_BEEP', 'PlayFrontEndSound(SOUND_FRONTEND_BEEP'):
            self.assertIn(token, script)
        self.assertNotIn('0xCD', script)

    def test_ped_crunch_case(self):
        source = read_source('stories/src/audio/AudioLogic.cpp')
        body = extract_function(source, 'cAudioManager::ProcessPedOneShots')
        self.assertIn('case SOUND_PED_CRUNCH', body)
        self.assertIn('SFX_PED_CRUNCH_1', body)

    def test_chainsaw_crunch_timer_in_padding(self):
        # VALIDATE_SIZE(CWeapon, 0x18) is a no-op unless CHECK_STRUCT_SIZES, so pin the size on a host mirror.
        header = read_source('stories/src/weapons/Weapon.h')
        self.assertRegex(header, r'bool m_bAddRotOffset;\s*\n\s*int8 m_nChainsawCrunchTimer;')
        compile_and_run(harness('weapon_padding.cpp'), sanitize=False)

    def test_chainsaw_emits_crunch(self):
        source = read_source('stories/src/weapons/Weapon.cpp')
        block = between(source, 'PARTICLE_DEBRIS2', 'ASSOCGRP_KNIFE')
        self.assertIn('SOUND_PED_CRUNCH', block)
        self.assertIn('m_nChainsawCrunchTimer', block)

    def test_setdie_player_crunch(self):
        source = read_source('stories/src/peds/Ped.cpp')
        body = extract_function(source, 'CPed::SetDie(AnimationId')
        for token in ('SOUND_PED_CRUNCH', 'bIsDrowning', 'Say(SOUND_PED_DAMAGE)'):
            self.assertIn(token, body)

    def test_carjacked_whoosh_case(self):
        source = read_source('stories/src/audio/AudioLogic.cpp')
        body = extract_function(source, 'cAudioManager::ProcessPedOneShots')
        self.assertIn('case SOUND_PED_CARJACKED_WHOOSH', body)
        self.assertIn('SFX_GOLF_CLUB_SWING', body)

    def test_dragged_from_car_sounds(self):
        source = read_source('stories/src/peds/PedAI.cpp')
        body = extract_function(source, 'CPed::BeingDraggedFromCar')
        for token in ('ANIM_STD_QUICKJACKED', 'SOUND_PED_CARJACKED_WHOOSH', 'SOUND_186', 'SOUND_187',
                      'SOUND_PED_DEFEND', 'SOUND_STEP_START', 'SOUND_STEP_END',
                      '- m_pVehicleAnim->timeStep <='):
            self.assertIn(token, body)

    def test_arrested_drag_does_not_double_emit_sounds(self):
        # PED_ARRESTED + last state PED_DRAG_FROM_CAR runs BeingDraggedFromCar from both
        # CPlayerPed::ProcessControl and CWorld::Process in one frame; only the world call may emit sounds.
        header = read_source('stories/src/peds/Ped.h')
        self.assertIn('void BeingDraggedFromCar(bool playSounds = true);', header)
        body = extract_function(read_source('stories/src/peds/PedAI.cpp'), 'CPed::BeingDraggedFromCar')
        self.assertIn('if (playSounds && soundTime >= 0.0f', body)
        player = read_source('stories/src/peds/PlayerPed.cpp')
        self.assertIn('BeingDraggedFromCar(false);', player)
        self.assertNotRegex(player, r'BeingDraggedFromCar\(\s*\)')
        world = read_source('stories/src/core/World.cpp')
        self.assertRegex(world, r'BeingDraggedFromCar\(\)')


if __name__ == '__main__':
    unittest.main()
