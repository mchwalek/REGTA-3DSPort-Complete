#!/usr/bin/env python3
"""Regression test for PS2 button names written literally in GXT text.

GXT key TUP_AD (the adrenaline pill help at the start of the TP1/TP2/TS1
bike side missions) says "Press R1 button" in every language, without a
~k~ token. The scripts poll IS_BUTTON_PRESSED 0 6 (RightShoulder1), which
is R on 3DS. Text.cpp rewrites the literal R1 to R for that key.

Extracts the real Replace3DSLiteralButtonText from Text.cpp, compiles it into
cpp/literal_button_text.cpp, and checks the rewrite. Also checks that
CText::Get calls it.
"""
import unittest

from cpptest import between, compile_and_run, extract_function, harness, read_source, strip_comments


class TestLiteralButtonText(unittest.TestCase):
    def setUp(self):
        self.src = read_source("stories/src/text/Text.cpp")

    def test_tup_ad_names_r(self):
        func = (extract_function(self.src, "static bool\nIsLiteralButtonBoundary3DS") +
                extract_function(self.src, "static wchar *\nReplace3DSLiteralButtonText"))
        compile_and_run(harness("literal_button_text.cpp", FUNCTION=func))

    def test_get_applies_rewrite(self):
        get = strip_comments(between(self.src, "wchar*\nCText::Get(", "\nwchar UpperCaseTable"))
        self.assertIn("Replace3DSLiteralButtonText(key, outstr)", get)


if __name__ == "__main__":
    unittest.main()
