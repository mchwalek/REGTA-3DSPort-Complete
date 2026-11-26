#!/usr/bin/env python3
"""The reLCS stats page must list the rows PS2 LCS lists, in PS2 order.

CStats::ConstructStatLine was reVC's and still listed Vice City stats
("Stores knocked off", "Assassination contracts completed", flight time and
pilot rank, fashion and property budgets, golf cart and heli distance). The
row order and conditions below come from PS2 CStats::ConstructStatLine
(SLES_541.35 0x231d50), including the LCS-only rows (odd jobs, races,
outfits) and the indent PS2 gives the race and outfit sub-rows.
"""
import re
import unittest

from cpptest import Program, between, extract_function, harness, read_source

STATIC = re.compile(r'^\tstatic ([\w ]+?) +(\w+)(\[\w+\])?;', re.M)

COMMON_HEAD = [
    'PER_COM', 'NMISON', 'ST_TIME', 'ST_OVTI', 'DAYSPS', 'NUMSHV', 'FEST_RP', 'PERPIC',
]
COMMON_MID = [
    'CAR_EXP', 'BOA_EXP', 'HEL_DST', 'TYREPOP', 'ST_STAR', 'ST_STGN', 'TM_BUST',
    'TM_DED', 'ST_HEAD', 'DAYPLC',
]
COMMON_KILLS = [
    'GNG_WST', 'DED_CRI', 'KGS_EXP', 'BUL_FIR', 'BUL_HIT', 'ACCURA', 'CAR_CRU',
    'FESTDFM', 'FESTDCM', 'DISTBIM', 'DISTBOM', 'TOTDISM',
    'MXCARDM', 'MXCARJM', 'MXFLIP', 'MXJUMP', 'BSTSTU',
]
BIKE = ['ST_WHEE', 'ST_WHED', 'ST_STOP', 'ST_STOD', 'ST_FAPD', 'ST_2WHE', 'ST_2WHD']
TAIL = ['SPRAYIN', 'ST_WEAP', 'ST_AUTO', 'ST_DAMA', 'CHASE', '>CHASE_STRING']

ZERO = (COMMON_HEAD + COMMON_MID + COMMON_KILLS + ['>NOSTUC', 'NOUNIF'] + BIKE + ['TMSOUT', 'ST_DRWN']
        + TAIL)

FULL = (COMMON_HEAD + ['PE_WAST', 'PE_WSOT'] + COMMON_MID + ['ST_GANG', '>ST_GNG9']
        + COMMON_KILLS[:2] + ['HTMKLD'] + COMMON_KILLS[2:]
        + ['>DBINST', 'NOUNIF'] + BIKE
        + ['ST_LOAN', 'FEST_CC', 'FEST_HV', 'PASDRO', 'MONTAX', 'FEST_LS', 'FEST_HA', 'FEST_FE', 'FIRELVL',
           'CARSLD', 'MONCAR', 'BIKESLD', 'MONBIKE', 'CARSEXP', 'SLTVLVL', 'SLTVMON', 'SLTVKIL', 'MONTRS',
           'GDAMSP', 'HGAJD', 'GDA_HL', 'COM_ZON', 'FSTTRT', 'BHLPOS', 'TMSOUT',
           'BNDRACE', 'BNDRAC1', 'DBIKEBP', 'DBIKEFL',
           'BSRPS2', 'DBIKEBP', 'DBIKEFL', 'DBIKEFT',
           'DBIKEHE', 'DBIKE0', 'DBIKEFL', 'DBIKEFT', 'DBIKEAI', 'FEST_GO',
           'ST_MOVI', 'ST_PHOT', 'ST_PIZZ', 'ST_NOOD', 'MO_TOUR', 'TA_TOUR', 'ST_GARB', 'ST_ICEC',
           'SC_SCRA', 'SC_9MM', 'SC_SCOO', 'SC_WICH', 'FEST_CN', 'FEST_TR',
           'ST_BRK', 'ST_LTBR', 'ST_DRWN', 'SEAGULL',
           'FST_MFR', '>FEA_FM9', 'FST_LFR', '>FEA_FM0'] + TAIL + ['OUTFITS', 'OUTF_00', 'OUTF_15'])

RACE_ROWS = (['BNDRACE'] + [k for i in range(3) for k in ('BNDRAC%d' % i, 'DBIKEBP', 'DBIKEFL')]
             + [k for i in range(6) for k in ('BSRPS%d' % i, 'DBIKEBP', 'DBIKEFL', 'DBIKEFT')]
             + ['DBIKEHE'] + [k for i in range(10) for k in ('DBIKE%d' % i, 'DBIKEFL', 'DBIKEFT')]
             + ['DBIKEAI'])
RACES = ZERO[:ZERO.index('TMSOUT') + 1] + RACE_ROWS + ZERO[ZERO.index('TMSOUT') + 1:]

# PS2 BuildStatLine (0x235448) indent of each sub-row. Other rows have 0.
INDENTS = {
    'COM_ZON': 4,
    'BNDRAC1': 2, 'BSRPS2': 0, 'DBIKE0': 2, 'DBIKEAI': 2,
    'OUTF_00': 4, 'OUTF_15': 4,
}
SUB_ROW_INDENTS = {'BNDRAC1': 4, 'BSRPS2': 2, 'DBIKE0': 4}

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


def _rows(output):
    lines = output.splitlines()
    assert lines[-1] == 'ok', output
    rows = []
    for line in lines[:-1]:
        left, right, indent = line.split('|')
        rows.append((left if left else '>' + right, right, int(indent)))
    return rows


def _keys(output):
    return [key for key, _, _ in _rows(output)]


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

    def test_every_race_finished_rows(self):
        self.assertEqual(_keys(self.program.run('races')), RACES)

    def test_air_time_needs_a_dirt_bike_race(self):
        self.assertEqual(_keys(self.program.run('air_only')), ZERO)

    def test_sub_row_indents(self):
        rows = _rows(self.program.run('full'))
        parent = None
        for key, _, indent in rows:
            if key in ('DBIKEBP', 'DBIKEFL', 'DBIKEFT'):
                self.assertEqual(indent, SUB_ROW_INDENTS[parent], (parent, key))
            else:
                self.assertEqual(indent, INDENTS.get(key, 0), key)
                parent = key

    def test_lcs_row_values(self):
        values = {key: right for key, right, _ in _rows(self.program.run('full'))}
        # Times are seconds shown as minutes and seconds, FEST_GO is milliseconds.
        self.assertEqual(values['FSTTRT'], '2/5')
        self.assertEqual(values['FEST_GO'], '1/5')
        self.assertEqual(values['CARSEXP'], '1/3')
        self.assertEqual(values['BHLPOS'], '2')
        # ST_TIME counts from the session start, ST_OVTI is the whole game (1:02).
        self.assertEqual(values['ST_TIME'], '1/0')
        self.assertEqual(values['ST_OVTI'], '1/2')

    def test_property_destroyed_value(self):
        self.assertEqual(self.program.run('damage').splitlines()[0], 'ST_DAMA=1234')


if __name__ == '__main__':
    unittest.main()
