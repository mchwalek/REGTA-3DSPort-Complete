#!/usr/bin/env python3
"""The reLCS stats page must list the rows PS2 LCS lists, in PS2 order.

CStats::ConstructStatLine was reVC's and still listed Vice City stats
("Stores knocked off", "Assassination contracts completed", flight time and
pilot rank, fashion and property budgets, golf cart and heli distance). The
row order and conditions below come from PS2 CStats::ConstructStatLine
(SLES_541.35 0x231d50). LCS-only rows that reLCS doesn't store yet are not
listed here.
"""
import re
import unittest

from cpptest import Program, between, extract_function, harness, read_source

STATIC = re.compile(r'^\tstatic ([\w ]+?) +(\w+)(\[\w+\])?;', re.M)

COMMON_HEAD = [
    'PER_COM', 'NMISON', 'ST_TIME', 'DAYSPS', 'NUMSHV', 'FEST_RP', 'PERPIC',
]
COMMON_MID = [
    'CAR_EXP', 'BOA_EXP', 'HEL_DST', 'TYREPOP', 'ST_STAR', 'ST_STGN', 'TM_BUST',
    'TM_DED', 'ST_HEAD', 'DAYPLC',
]
COMMON_KILLS = [
    'GNG_WST', 'DED_CRI', 'KGS_EXP', 'BUL_FIR', 'BUL_HIT', 'ACCURA',
    'FESTDFM', 'FESTDCM', 'DISTBIM', 'DISTBOM', 'TOTDISM',
    'MXCARDM', 'MXCARJM', 'MXFLIP', 'MXJUMP', 'BSTSTU',
]
BIKE = ['ST_WHEE', 'ST_WHED', 'ST_STOP', 'ST_STOD', 'ST_2WHE', 'ST_2WHD']
TAIL = ['SPRAYIN', 'ST_WEAP', 'ST_AUTO', 'ST_DAMA', 'CHASE', '>CHASE_STRING']

ZERO = COMMON_HEAD + COMMON_MID + COMMON_KILLS + ['>NOSTUC', 'NOUNIF'] + BIKE + ['ST_DRWN'] + TAIL

FULL = (COMMON_HEAD + ['PE_WAST', 'PE_WSOT'] + COMMON_MID + ['ST_GANG', '>ST_GNG9'] + COMMON_KILLS
        + ['>DBINST', 'NOUNIF'] + BIKE
        + ['ST_LOAN', 'FEST_CC', 'FEST_HV', 'PASDRO', 'MONTAX', 'FEST_LS', 'FEST_HA', 'FEST_FE', 'FIRELVL',
           'ST_MOVI', 'ST_PHOT', 'ST_PIZZ', 'ST_GARB', 'ST_ICEC',
           'ST_BRK', 'ST_LTBR', 'ST_DRWN', 'SEAGULL',
           'FST_MFR', '>FEA_FM9', 'FST_LFR', '>FEA_FM0'] + TAIL)

VC_ONLY = ['ST_STOR', 'ST_ASSI', 'ST_FTIM', 'ST_PRAN', 'ST_FASH', 'ST_PROP', 'DISTGOL', 'DISTGOM',
           'DISTHEL', 'DISTHEM', 'MXCARD', 'MXCARJ']


def _source():
    stats_h = read_source('stories/src/core/Stats.h')
    cls = between(stats_h, 'class CStats', '\n};', include_end=True)
    statics = []
    for type_, name, dims in STATIC.findall(cls):
        statics.append('%s CStats::%s%s;' % (type_, name, dims))
    enums = (between(read_source('stories/src/peds/PedType.h'), 'enum ePedType', '};', include_end=True) + '\n'
             + between(read_source('stories/src/audio/audio_enums.h'), 'enum eRadioStation', '};', include_end=True))
    func = 'int\n' + extract_function(read_source('stories/src/core/Stats.cpp'), 'CStats::ConstructStatLine(int rowIdx)')
    return harness('stats_lines.cpp', ENUMS=enums, CLASS=cls, STATICS='\n'.join(statics), FUNCTION=func)


def _keys(output):
    lines = output.splitlines()
    assert lines[-1] == 'ok', output
    return [left if left else '>' + right for left, right in (line.split('|', 1) for line in lines[:-1])]


class TestLcsStatsLines(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.program = Program(_source())

    @classmethod
    def tearDownClass(cls):
        cls.program.close()

    def test_harness_config_matches_stories(self):
        config = read_source('stories/src/core/config.h')
        for flag in ('FIX_BUGS', 'USE_MEASUREMENTS_IN_METERS'):
            self.assertRegex(config, r'(?m)^#define %s\b' % flag)
        self.assertNotRegex(config, r'(?m)^#define MORE_LANGUAGES\b')

    def test_fresh_stats_rows(self):
        self.assertEqual(_keys(self.program.run('zero')), ZERO)

    def test_all_stats_set_rows(self):
        self.assertEqual(_keys(self.program.run('full')), FULL)

    def test_no_vice_city_rows(self):
        for scenario in ('zero', 'full'):
            keys = _keys(self.program.run(scenario))
            for key in VC_ONLY:
                self.assertNotIn(key, keys, scenario)

    def test_property_destroyed_value(self):
        self.assertEqual(self.program.run('damage').splitlines()[0], 'ST_DAMA=1234')


if __name__ == '__main__':
    unittest.main()
