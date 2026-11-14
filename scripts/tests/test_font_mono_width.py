#!/usr/bin/env python3
"""Right-justified monospaced HUD text (mission timer and counters, e.g. the
taxi FARES counter) on stories.

1. CFont::GetCharacterSize scaled only the incrementer for monospaced glyphs
   (`Size[418] + incr * scaleX`), so PrintString laid right-justified text out
   several times wider than RenderFontBuffer drew it, and it ended short of its
   right anchor. PS2 (SLES_541.35 0x167250) scales the whole sum.
2. CFont::PrintString never stored Details.rightJustify into the queued
   CFontRenderState, so PrintChar's per-glyph right-alignment read leftover
   buffer bytes, and counter digits shifted whenever the blinking timer changed
   the buffer layout. PS2 PrintString (0x1658f0 -> 0x165418) stores it at +0x38.
"""
import re
import unittest

from cpptest import Program, between, extract_function, harness, read_source, strip_comments

FONT = 'stories/src/renderer/Font.cpp'


class FontMonoWidth(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        src = read_source(FONT)
        funcs = ''.join(extract_function(src, sig) for sig in (
            'float\nCFont::GetCharacterWidth(wchar c, bool forceProportional)',
            'float\nCFont::GetCharacterSize(wchar c)',
            'float\nCFont::GetStringWidth(wchar *s, bool spaces)'))
        cls.program = Program(harness(
            'font_mono_width.cpp',
            SIZE_TABLE=between(src, 'int16 CFont::Size[MAX_FONTS][419] = {', '\n};', include_end=True) + '\n'
            + between(src, 'int FontSizeIncrementers[] =', ';', include_end=True) + '\n',
            IS_PUNCTUATION=extract_function(src, 'bool IsPunctuation(wchar c)'),
            WIDTH_FUNCS=funcs))
        cls.src = src

    @classmethod
    def tearDownClass(cls):
        cls.program.close()

    def test_monospace_layout_width_matches_render(self):
        self.assertEqual(self.program.run('monospace_layout_width_matches_render').strip(), 'ok')

    def test_proportional_layout_width_matches_render(self):
        self.assertEqual(self.program.run('proportional_layout_width_matches_render').strip(), 'ok')

    def test_print_string_queues_right_justify(self):
        body = strip_comments(extract_function(
            self.src, 'void\nCFont::PrintString(float x, float y, uint32, wchar *start, wchar *end, float spwidth)'))
        self.assertRegex(body, re.compile(r'pRenderState->rightJustify\s*=\s*Details\.rightJustify\s*;'))


if __name__ == '__main__':
    unittest.main()
