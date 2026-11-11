#!/usr/bin/env python3
"""Exercise the real 3DS tick-to-double conversion against host arithmetic.

Regression test for: psTimer() reads svcGetSystemTick(), a 64-bit counter.
The ARM11 VFP cannot convert 64-bit integers to floating point, so the
conversion is hand-split into high and low 32-bit words (mirroring
common/libctru/source/os.c:13).  A dropped or mis-scaled high word would
still produce a plausible-looking clock, so pin the arithmetic exactly.
"""
import unittest

from cpptest import compile_and_run, extract_function, harness, read_source, strip_comments


class TimerPrecision(unittest.TestCase):
    def test_tick_conversion_is_exact(self):
        source = read_source('stories/src/skel/3ds/3ds.cpp')
        convert = extract_function(source, 'TicksToDouble(u64 value)')
        # Recover the 'static inline double' return type that precedes the
        # signature line, so the extracted fragment compiles standalone.
        convert = 'static inline double\n' + convert
        compile_and_run(harness('timer_precision.cpp', FUNCTION=convert))

    def test_psTimer_does_not_use_osGetTime(self):
        # osGetTime() truncates to whole milliseconds; reintroducing it would
        # silently restore the timestep quantisation this change removed.
        # osGetTime() is named in psTimer's explanatory comment, and the live
        # call is osGetTimeRef() which contains 'osGetTime' as a substring, so
        # the check has to look at code only, and at 'osGetTime('.
        source = read_source('stories/src/skel/3ds/3ds.cpp')
        body = strip_comments(extract_function(source, 'psTimer(void)'))
        self.assertNotIn('osGetTime(', body)
        self.assertIn('svcGetSystemTick(', body)


if __name__ == '__main__':
    unittest.main()
