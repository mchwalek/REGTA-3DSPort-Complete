// Harness for test_menu_helper_text.py: GetDefaultHelperTextKey from
// stories/src/core/Frontend.cpp is pasted in at the marker below.
// Built twice: with -D_3DS and without.
#include "stubs.h"

enum {
	MENUACTION_NO = 1,
	MENUACTION_MUSICVOLUME,
	MENUACTION_SFXVOLUME,
	MENUACTION_KEYBOARDCTRLS,
	MENUACTION_SCREENRES,
	MENUACTION_AUDIOHW,
	MENUACTION_SPEAKERCONF,
	MENUACTION_RESTOREDEF,
	MENUACTION_MP3VOLUMEBOOST,
	MENUACTION_BRIGHTNESS,
};
enum { MENUPAGE_STATS = 0, MENUPAGE_DISPLAY_SETTINGS = 4 };

/*@FUNCTION@*/

static void check(int32 action, int32 screen, bool noAudio, bool notLoaded, const char *pc, const char *ds)
{
	const char *key = GetDefaultHelperTextKey(action, screen, noAudio, notLoaded);
#ifdef _3DS
	const char *want = ds;
#else
	const char *want = pc;
#endif
	if (want == nil)
		assert(key == nil);
	else
		assert(key != nil && strcmp(key, want) == 0);
}

int main()
{
	const int32 S = MENUPAGE_DISPLAY_SETTINGS;
	check(MENUACTION_NO, S, false, false, nil, nil);
	check(MENUACTION_KEYBOARDCTRLS, S, false, false, nil, nil);
	check(MENUACTION_RESTOREDEF, S, false, false, nil, nil);

	const int32 audio[] = { MENUACTION_MUSICVOLUME, MENUACTION_SFXVOLUME, MENUACTION_AUDIOHW,
	                        MENUACTION_SPEAKERCONF, MENUACTION_MP3VOLUMEBOOST };
	for (int32 a : audio) {
		check(a, S, true, false, "FEH_NA", "FEH_NA");
		check(a, S, false, false, "FET_MIG", nil);
	}

	check(MENUACTION_SCREENRES, S, false, true, "FET_MIG", nil);
	check(MENUACTION_SCREENRES, S, false, false, "FEH_NA", "FEH_NA");

	check(MENUACTION_BRIGHTNESS, S, false, false, "FET_MIG", nil);
	check(MENUACTION_BRIGHTNESS, MENUPAGE_STATS, false, false, "FEH_SSA", nil);
	return 0;
}
