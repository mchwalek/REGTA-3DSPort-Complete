#!/usr/bin/env python3
"""Exercise the real CFont::ParseToken against host stubs.

Regression test for: garbled R3/L3 help text (e.g. the Taxi Driver side
mission's "Press ~k~ ~TGSUB~" cancel prompt). The 3DS touch-instruction
rewrite in CMessages::Normalize3DSTouchInstructionPrefix (text/Messages.cpp)
produces adjacent tokens like "~w~~h~TOUCH, THEN TAP R3 ...". LCS dropped
reVC's adjacent-token recursion in ParseToken, so CFont::RenderFontBuffer
printed the next token's opening '~' as a literal glyph and desynced the
parse, misfiring a button-icon sprite from the following text. See
stories/src/renderer/Font.cpp, CFont::ParseToken.
"""
import unittest

from cpptest import Program, extract_function, harness, read_source


class FontTokenParsing(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        parse_token = extract_function(
            read_source('stories/src/renderer/Font.cpp'),
            'wchar*\nCFont::ParseToken(wchar* str, CRGBA &color, bool &flash, bool &bold)')
        body = parse_token.replace('CFont::ParseToken', 'ParseToken')
        cls.fixed = Program(harness('font_tokens.cpp', FIX_BUGS='#define FIX_BUGS', PARSE_TOKEN=body))
        cls.unfixed = Program(harness('font_tokens.cpp', FIX_BUGS='', PARSE_TOKEN=body))

    @classmethod
    def tearDownClass(cls):
        cls.fixed.close()
        cls.unfixed.close()

    def test_adjacent_color_tokens_consumed_without_literal_tilde(self):
        self.assertEqual(self.fixed.run('adjacent_color_tokens_consumed_without_literal_tilde').strip(), 'ok')

    def test_adjacent_token_then_button_icon_fires_correctly(self):
        self.assertEqual(self.fixed.run('adjacent_token_then_button_icon_fires_correctly').strip(), 'ok')

    def test_without_fix_bugs_desyncs_on_adjacent_tokens(self):
        self.assertEqual(self.unfixed.run('without_fix_bugs_desyncs_on_adjacent_tokens').strip(), 'ok')


if __name__ == '__main__':
    unittest.main()
