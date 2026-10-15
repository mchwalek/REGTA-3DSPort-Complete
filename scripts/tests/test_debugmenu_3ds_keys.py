#!/usr/bin/env python3
"""Compile the real 3DS debug-menu key mapping against host stubs."""
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


def function(source, signature):
    start = source.index(signature)
    end = source.index('\n}', start) + 2
    return source[start:end]


class DebugMenu3DSKeys(unittest.TestCase):
    def test_key_mask_table(self):
        source = (ROOT / 'stories/src/extras/debugmenu.cpp').read_text()
        fn = function(source, 'static u32\nMenu3DSKeyMask(int key)')

        cpp = r'''
#include <cassert>
typedef unsigned int u32;
enum { KEY_A = 1u<<0, KEY_B = 1u<<1, KEY_SELECT = 1u<<2, KEY_START = 1u<<3,
       KEY_DRIGHT = 1u<<4, KEY_DLEFT = 1u<<5, KEY_DUP = 1u<<6, KEY_DDOWN = 1u<<7,
       KEY_R = 1u<<8, KEY_L = 1u<<9, KEY_X = 1u<<10, KEY_Y = 1u<<11 };
enum { rsUP = 1, rsDOWN, rsLEFT, rsRIGHT, rsPGUP, rsPGDN, rsENTER, rsBACKSP,
       rsLSHIFT, rsRSHIFT, rsLCTRL, rsF1 };
''' + fn + r'''
int main() {
 assert(Menu3DSKeyMask(rsUP) == KEY_DUP);
 assert(Menu3DSKeyMask(rsDOWN) == KEY_DDOWN);
 assert(Menu3DSKeyMask(rsLEFT) == KEY_DLEFT);
 assert(Menu3DSKeyMask(rsRIGHT) == KEY_DRIGHT);
 assert(Menu3DSKeyMask(rsPGUP) == KEY_L);
 assert(Menu3DSKeyMask(rsPGDN) == KEY_R);
 assert(Menu3DSKeyMask(rsENTER) == KEY_A);
 assert(Menu3DSKeyMask(rsBACKSP) == KEY_B);
 assert(Menu3DSKeyMask(rsLSHIFT) == KEY_Y);
 assert(Menu3DSKeyMask(rsRSHIFT) == KEY_Y);
 assert(Menu3DSKeyMask(rsLCTRL) == 0);
 assert(Menu3DSKeyMask(rsF1) == 0);
 assert(Menu3DSKeyMask('M') == 0);
 return 0;
}
'''
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / 't.cpp'
            exe = Path(tmp) / 't'
            src.write_text(cpp)
            subprocess.run(['c++', '-std=c++11', str(src), '-o', str(exe)], check=True)
            subprocess.run([str(exe)], check=True)


if __name__ == '__main__':
    unittest.main()
