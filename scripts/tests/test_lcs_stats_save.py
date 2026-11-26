#!/usr/bin/env python3
"""The 3DS stats save block must keep loading saves from older builds.

On 3DS CStats::SaveStats writes a raw copy of the stats with no version.
The LCS-only stats (odd jobs, races, costumes) were added after the end of
the old block. An old block is shorter, so LoadStats must stop after the
old fields and give the new ones the PS2 CStats::Init start values
(SLES_541.35: 0, and INT_MAX for race positions). The setters follow the PS2
opcode handlers (0x231c60..0x231d38, 0x2303e8..0x2304f8, 0x2319c8).
"""
import re
import unittest

from cpptest import Program, between, extract_function, harness, read_source

STATIC = re.compile(r'^\tstatic ([\w ]+?) +(\w+)(\[\w+\])?;', re.M)

# The stats block of saves written before the LCS-only stats, in save order.
# This is the on-card layout of existing 3DS saves: do not change it.
OLD_FIELDS = '''
PeopleKilledByPlayer PeopleKilledByOthers CarsExploded BoatsExploded TyresPopped RoundsFiredByPlayer
PedsKilledOfThisType HelisDestroyed ProgressMade TotalProgressInGame KgsOfExplosivesUsed BulletsThatHit
HeadsPopped WantedStarsAttained WantedStarsEvaded TimesArrested TimesDied DaysPassed SafeHouseVisits
Sprayings MaximumJumpDistance MaximumJumpHeight MaximumJumpFlips MaximumJumpSpins BestStuntJump
NumberOfUniqueJumpsFound TotalNumberOfUniqueJumps MissionsGiven PassengersDroppedOffWithTaxi
MoneyMadeWithTaxi IndustrialPassed CommercialPassed SuburbanPassed PamphletMissionPassed NoMoreHurricanes
DistanceTravelledOnFoot DistanceTravelledByCar DistanceTravelledByBike DistanceTravelledByBoat
DistanceTravelledByGolfCart DistanceTravelledByHelicoptor DistanceTravelledByPlane LivesSavedWithAmbulance
CriminalsCaught FiresExtinguished HighestLevelVigilanteMission HighestLevelAmbulanceMission
HighestLevelFireMission PhotosTaken NumberKillFrenziesPassed TotalNumberKillFrenzies TotalNumberMissions
FlightTime TimesDrowned SeagullsKilled WeaponBudget FashionBudget LoanSharks StoresKnockedOff MovieStunts
Assassinations PizzasDelivered GarbagePickups IceCreamSold TopShootingRangeScore ShootingRank
LongestWheelie LongestStoppie Longest2Wheel LongestWheelieDist LongestStoppieDist Longest2WheelDist
PropertyBudget AutoPaintingBudget PropertyDestroyed NumPropertyOwned BloodRingKills BloodRingTime
PropertyOwned HighestChaseValue FastestTimes HighestScores BestPositions KillsSinceLastCheckpoint
TotalLegitimateKills LastMissionPassedName CheatedCount FavoriteRadioStationList
'''.split()

SETTERS = [
    'static void RegisterBestTime(int32 &best, int32 time)',
    'void CStats::InitLcsStats(void)',
    'void CStats::RegisterFastestSmugglingTime(int32 time)',
    'void CStats::RegisterHighestGuardianAngelJusticeDished(int32)',
    'void CStats::RegisterGuardianAngelLevels(int32 ind, int32 com, int32 sub)',
    'void CStats::RegisterBestBanditLapTime(int32 race, int32 time)',
    'void CStats::RegisterBestBanditPosition(int32 race, int32 position)',
    'void CStats::RegisterMostTimeLeftTrainRace(int32 time)',
    'void CStats::RegisterHighestTrainCashEarned(int32 cash)',
    'void CStats::RegisterFastestHeliRaceTime(int32 time)',
    'void CStats::RegisterBestHeliRacePosition(int32 position)',
    'void CStats::RegisterStreetRaceFastestTime(int32 race, int32 time)',
    'void CStats::RegisterStreetRaceFastestLap(int32 race, int32 time)',
    'void CStats::RegisterStreetRaceBestPosition(int32 race, int32 position)',
    'void CStats::RegisterDirtBikeFastestLap(int32 race, int32 time)',
    'void CStats::RegisterDirtBikeFastestTime(int32 race, int32 time)',
    'void CStats::RegisterBestTimeGoGoFaggio(int32 time)',
    'void CStats::AddUnlockedCostume(int32 costume)',
    'static uint32 LcsStatsSize(void)',
    'void CStats::SaveStats(uint8 *buf, uint32 *size)',
    'void CStats::LoadStats(uint8 *buf, uint32 size)',
]


def _x_macro(name, fields):
    return '#define %s(X) %s' % (name, ' '.join('X(%s)' % f for f in fields))


def _lcs_fields(cls):
    block = between(cls, '// LCS-only stats', 'SessionStartTime')
    return [name for _, name, _ in STATIC.findall(block)]


def _source():
    stats_h = read_source('stories/src/core/Stats.h')
    cls = between(stats_h, 'class CStats', '\n};', include_end=True)
    statics = ['%s CStats::%s%s;' % m for m in STATIC.findall(cls)]
    enums = (between(read_source('stories/src/peds/PedType.h'), 'enum ePedType', '};', include_end=True) + '\n'
             + between(read_source('stories/src/audio/audio_enums.h'), 'enum eRadioStation', '};', include_end=True))
    stats_cpp = read_source('stories/src/core/Stats.cpp')
    funcs = '\n'.join(extract_function(stats_cpp, sig) for sig in SETTERS)
    return harness('stats_save.cpp', ENUMS=enums, CLASS=cls, STATICS='\n'.join(statics),
                   OLD_FIELDS=_x_macro('OLD_FIELDS', OLD_FIELDS),
                   LCS_FIELDS=_x_macro('LCS_FIELDS', _lcs_fields(cls)), FUNCTIONS=funcs)


class TestLcsStatsSave(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.program = Program(_source())

    @classmethod
    def tearDownClass(cls):
        cls.program.close()

    def test_lcs_fields_are_declared(self):
        cls = between(read_source('stories/src/core/Stats.h'), 'class CStats', '\n};')
        fields = _lcs_fields(cls)
        self.assertIn('CarsCrushed', fields)
        self.assertIn('UnlockedCostumes', fields)
        self.assertFalse(set(fields) & set(OLD_FIELDS))

    def test_round_trip_keeps_old_layout(self):
        self.assertEqual(self.program.run('roundtrip'), 'ok\n')

    def test_old_save_gets_start_values(self):
        self.assertEqual(self.program.run('old_save'), 'ok\n')

    def test_start_values(self):
        out = self.program.run('defaults').splitlines()
        self.assertEqual(out[-1], 'ok')
        expected = (['BestHeliRacePosition[0]=2147483647']
                    + ['BestBanditPositions[%d]=2147483647' % i for i in range(3)]
                    + ['StreetRaceBestPosition[%d]=2147483647' % i for i in range(6)])
        self.assertEqual(sorted(out[:-2]), sorted(expected))
        self.assertEqual(out[-2], 'UnlockedCostumes=0')

    def test_setters_follow_ps2(self):
        self.assertEqual(self.program.run('setters').splitlines(), [
            'smuggling=40',
            'train=45',
            'traincash=10',
            'heli=80,3',
            'justice=2',
            'angel=2,3,1',
            'bandit=60,2',
            'street=90,30,2',
            'dirt=33,99',
            'gogo=65000',
            'costumes=32769',
            'ok',
        ])


if __name__ == '__main__':
    unittest.main()
