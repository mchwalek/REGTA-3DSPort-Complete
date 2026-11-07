// Harness for test_map_legend_labels.py: CRadar::GetBlipLegendKey from
// stories/src/core/Radar.cpp is pasted in at the marker below.
#include "stubs.h"

enum { RADAR_SPRITE_ENTITY_BLIP = -2, RADAR_SPRITE_COORD_BLIP = -1 };
struct CRadar { static const char *GetBlipLegendKey(int32 sprite, const CRGBA &colour); };

/*@FUNCTION@*/

static void check(int32 sprite, uint8 r, uint8 g, uint8 b, const char *key)
{
	assert(strcmp(CRadar::GetBlipLegendKey(sprite, CRGBA(r, g, b, 255)), key) == 0);
}

int main()
{
	const int32 E = RADAR_SPRITE_ENTITY_BLIP, C = RADAR_SPRITE_COORD_BLIP;
	check(E, 255, 72, 77, "LG_51");   // red: Threat
	check(E, 127, 0, 0, "LG_51");     // dim red
	check(E, 95, 160, 106, "LG_53");  // green: Pick up
	check(E, 0, 127, 0, "LG_53");     // dim green
	check(E, 72, 77, 255, "LG_52");   // blue: Friend
	check(E, 255, 255, 0, "LG_52");   // any other colour: Friend
	check(C, 72, 77, 255, "LG_52");   // blue coord: Friend
	check(C, 0, 0, 127, "LG_52");     // dim blue coord
	check(C, 255, 72, 77, "LG_35");   // red coord: Destination
	check(C, 255, 255, 0, "LG_35");   // yellow coord: Destination
	return 0;
}
