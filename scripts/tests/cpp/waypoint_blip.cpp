// Harness for test_waypoint_blip.py: CRadar::ToggleTargetMarker from
// stories/src/core/Radar.cpp is pasted in at the marker below.
#include "stubs.h"

enum { NUMRADARBLIPS = 75 };
enum { BLIP_NONE, BLIP_CAR, BLIP_CHAR, BLIP_OBJECT, BLIP_COORD };
enum { BLIP_DISPLAY_NEITHER, BLIP_DISPLAY_MARKER_ONLY, BLIP_DISPLAY_BLIP_ONLY, BLIP_DISPLAY_BOTH };
enum { RADAR_TRACE_RED, RADAR_TRACE_GREEN, RADAR_TRACE_LIGHT_BLUE, RADAR_TRACE_GRAY };
enum { RADAR_SPRITE_NONE = 0, RADAR_SPRITE_MPOBJECTIVE = 49 };
struct sRadarTrace {
	uint32 m_nColor; uint32 m_eBlipType; int32 m_nEntityHandle; CVector m_vec2DPos; CVector m_vecPos;
	uint16 m_BlipIndex; bool m_bDim; bool m_bInUse; bool m_bShortRange; bool m_unused; float m_Radius;
	int16 m_wScale; uint16 m_eBlipDisplay; uint16 m_eRadarSprite;
};
struct CRadar {
	static sRadarTrace ms_RadarTrace[NUMRADARBLIPS];
	static int TargetMarkerId;
	static CVector TargetMarkerPos;
	static void ToggleTargetMarker(float, float);
	static int32 GetNewUniqueBlipIndex(int32 i) { return i; }
	static void ClearBlip(int32 i) { ms_RadarTrace[i].m_bInUse = false; }
};
sRadarTrace CRadar::ms_RadarTrace[NUMRADARBLIPS];
int CRadar::TargetMarkerId = -1;
CVector CRadar::TargetMarkerPos;

/*@FUNCTION@*/

int main()
{
	CRadar::ToggleTargetMarker(10.0f, 20.0f);
	assert(CRadar::TargetMarkerId >= 0);
	const sRadarTrace &t = CRadar::ms_RadarTrace[CRadar::TargetMarkerId];
	assert(t.m_bInUse && t.m_eBlipType == BLIP_COORD);
	assert(t.m_nColor == RADAR_TRACE_RED && t.m_bDim == 1);
	assert(t.m_eRadarSprite == RADAR_SPRITE_MPOBJECTIVE);
	assert(t.m_wScale == 1 && t.m_eBlipDisplay == BLIP_DISPLAY_BLIP_ONLY);
	assert(t.m_vecPos.x == 10.0f && t.m_vecPos.y == 20.0f && t.m_vecPos.z == 0.0f);
	CRadar::ToggleTargetMarker(0.0f, 0.0f);
	assert(CRadar::TargetMarkerId == -1);
	return 0;
}
