// Harness for test_ps2_absent_instances.py: IsInstanceAbsentOnPS2 from
// stories/src/core/FileLoader.cpp and CGeneral::faststricmp from
// stories/src/core/General.h are pasted in at the markers below.
#include "stubs.h"
#include <ctype.h>

class CGeneral
{
public:
	/*@FASTSTRICMP@*/
};

/*@FUNCTION@*/

int main()
{
	assert(IsInstanceAbsentOnPS2("Trans_lights01"));
	assert(IsInstanceAbsentOnPS2("Trans_lights02"));
	assert(IsInstanceAbsentOnPS2("Trans_lights03"));
	assert(IsInstanceAbsentOnPS2("trans_lights01"));
	assert(IsInstanceAbsentOnPS2("TRANS_LIGHTS03"));

	assert(!IsInstanceAbsentOnPS2("Section_01"));
	assert(!IsInstanceAbsentOnPS2("Section_1road"));
	assert(!IsInstanceAbsentOnPS2("hill_tunnel1"));
	assert(!IsInstanceAbsentOnPS2("LODl_tunnel1"));
	assert(!IsInstanceAbsentOnPS2("dead_end"));
	assert(!IsInstanceAbsentOnPS2("Trans_lights01b"));
	assert(!IsInstanceAbsentOnPS2("Trans_lights0"));
	assert(!IsInstanceAbsentOnPS2("Trans_lights04"));
	assert(!IsInstanceAbsentOnPS2(""));
	return 0;
}
