#!/usr/bin/env python3
"""Compile the real 3DS debug-menu key mapping against host stubs."""
import unittest

from cpptest import compile_and_run, extract_function, harness, read_source


class DebugMenu3DSKeys(unittest.TestCase):
    def test_key_mask_table(self):
        fn = extract_function(read_source('stories/src/extras/debugmenu.cpp'), 'static u32\nMenu3DSKeyMask(int key)')
        compile_and_run(harness('debugmenu_3ds_keys.cpp', FUNCTION=fn), sanitize=False)


if __name__ == '__main__':
    unittest.main()
