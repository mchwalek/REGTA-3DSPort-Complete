#!/usr/bin/env python3
"""Exercise the real 3DS weapon-suppression latch against host stubs.

Regression test for: menu accept (Circle/A) is also the weapon-fire button.
A press held while a script menu (e.g. the clothes shop) disables player
controls must not fire the weapon the instant controls are re-enabled.
"""
import unittest

from cpptest import Program, extract_function, harness, read_source


class MenuInputLatch(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        source = read_source('stories/src/core/Pad.cpp')
        raw = extract_function(source, 'int32 CPad::GetWeaponButtonRaw(void)')
        get_weapon = extract_function(source, 'int32 CPad::GetWeapon(void)')
        update = extract_function(source, 'void CPad::UpdateWeaponSuppression(void)')
        # Paste as in-class members of the stub CPad.
        methods = (raw.replace('int32 CPad::', 'int ').replace('CPad::', '') +
                   get_weapon.replace('int32 CPad::', 'int ').replace('CPad::', '') +
                   update.replace('void CPad::', 'void ').replace('CPad::', ''))
        cls.program = Program(harness('menu_input_latch.cpp', METHODS=methods))

    @classmethod
    def tearDownClass(cls):
        cls.program.close()

    def _scenario(self, name):
        self.assertEqual(self.program.run(name).strip(), 'ok')

    def test_weapon_suppressed_across_menu_close(self):
        self._scenario('weapon_suppressed_across_menu_close')

    def test_unaffected_when_never_disabled(self):
        # Ordinary gameplay firing (never went through a disabled-controls
        # window) must be completely unaffected by the latch.
        self._scenario('unaffected_when_never_disabled')


if __name__ == '__main__':
    unittest.main()
