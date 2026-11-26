#!/usr/bin/env python3
"""Regression test: ETC1 decode and box downsample for the radar-tile mipmaps.

The 3DS pause-menu map shows the 128x128 radar tiles at about 3x
minification, so the tiles get mip levels at load
(rasterGenerateCompressedMipmaps). The SD card holds the tiles only as ETC
data, so level 0 is decoded, box-filtered and compressed again.
etc1_decode must be the exact inverse of the block order that texCompress
and etc1_common write. Otherwise the smaller levels come out scrambled.

Links the real compress.cpp and rg_etc1.cpp, and extracts the tile loop of
texCompress from 3dsraster.cpp into cpp/etc1_mipmaps.cpp.
"""
import unittest

from cpptest import ROOT, Program, between, harness, read_source

TEX = ROOT / "common/librw/src/3ds/tex"


class TestEtc1Mipmaps(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        loop = between(read_source("common/librw/src/3ds/3dsraster.cpp"),
                       "\tint x, y;\n\tuint8 *block;", "\n\tif(dst != end)", include_end=False)
        cls.program = Program(harness("etc1_mipmaps.cpp", TILE_LOOP=loop),
                              # the game builds with -fpermissive (stories/build/GNUmakefile)
                              flags=("-fpermissive", "-w", "-I", str(TEX), str(TEX / "compress.cpp"), str(TEX / "rg_etc1.cpp")))

    @classmethod
    def tearDownClass(cls):
        cls.program.close()

    def _scenario(self, name):
        self.assertEqual(self.program.run(name).strip(), "ok")

    def test_decode_round_trips_etc1a4(self):
        self._scenario("decode_round_trips_etc1a4")

    def test_decode_round_trips_etc1(self):
        self._scenario("decode_round_trips_etc1")

    def test_downsample_averages_2x2(self):
        self._scenario("downsample_averages_2x2")


if __name__ == "__main__":
    unittest.main()
