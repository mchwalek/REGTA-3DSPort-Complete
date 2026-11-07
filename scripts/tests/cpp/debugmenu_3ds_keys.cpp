// Harness for test_debugmenu_3ds_keys.py: Menu3DSKeyMask from
// stories/src/extras/debugmenu.cpp is pasted in at the marker below.
#include <cassert>
typedef unsigned int u32;
enum { KEY_A = 1u<<0, KEY_B = 1u<<1, KEY_SELECT = 1u<<2, KEY_START = 1u<<3,
	KEY_DRIGHT = 1u<<4, KEY_DLEFT = 1u<<5, KEY_DUP = 1u<<6, KEY_DDOWN = 1u<<7,
	KEY_R = 1u<<8, KEY_L = 1u<<9, KEY_X = 1u<<10, KEY_Y = 1u<<11 };
enum { rsUP = 1, rsDOWN, rsLEFT, rsRIGHT, rsPGUP, rsPGDN, rsENTER, rsBACKSP,
	rsLSHIFT, rsRSHIFT, rsLCTRL, rsF1 };

/*@FUNCTION@*/

int main() {
	assert(Menu3DSKeyMask(rsUP) == KEY_DUP);
	assert(Menu3DSKeyMask(rsDOWN) == KEY_DDOWN);
	assert(Menu3DSKeyMask(rsLEFT) == KEY_DLEFT);
	assert(Menu3DSKeyMask(rsRIGHT) == KEY_DRIGHT);
	assert(Menu3DSKeyMask(rsPGUP) == KEY_L);
	assert(Menu3DSKeyMask(rsPGDN) == KEY_R);
	assert(Menu3DSKeyMask(rsENTER) == KEY_A);
	assert(Menu3DSKeyMask(rsBACKSP) == KEY_B);
	assert(Menu3DSKeyMask(rsLSHIFT) == KEY_Y);
	assert(Menu3DSKeyMask(rsRSHIFT) == KEY_Y);
	assert(Menu3DSKeyMask(rsLCTRL) == 0);
	assert(Menu3DSKeyMask(rsF1) == 0);
	assert(Menu3DSKeyMask('M') == 0);
	return 0;
}
