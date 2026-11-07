// Harness for test_3ds_timer_precision.py: TicksToDouble from
// stories/src/skel/3ds/3ds.cpp is pasted in at the marker below.
#include <cassert>
#include <cstdint>
typedef uint64_t u64;
typedef uint32_t u32;

/*@FUNCTION@*/

int main() {
	// Zero and the low word in isolation.
	assert(TicksToDouble(0ULL) == 0.0);
	assert(TicksToDouble(1ULL) == 1.0);
	assert(TicksToDouble(0xFFFFFFFFULL) == 4294967295.0);

	// The 32-bit boundary: the high word must contribute, scaled by 2^32.
	assert(TicksToDouble(0x100000000ULL) == 4294967296.0);
	assert(TicksToDouble(0x1FFFFFFFFULL) == 8589934591.0);

	// Both words populated.
	assert(TicksToDouble(0x123456789ABCDEFULL) == 81985529216486895.0);

	// ~30 days of uptime at the 268 MHz tick rate stays exact:
	// 30 * 24 * 3600 * 268111856 = 694945930752000, well inside 2^53.
	u64 month = 694945930752000ULL;
	assert(TicksToDouble(month) == 694945930752000.0);

	// A one-tick difference at that magnitude is still resolvable, which is
	// what CTimer's per-frame delta depends on.
	assert(TicksToDouble(month + 1ULL) - TicksToDouble(month) == 1.0);
}
