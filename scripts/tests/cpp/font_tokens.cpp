// Harness for test_font_tokens.py: CFont::ParseToken(wchar*, CRGBA&, bool&, bool&)
// from stories/src/renderer/Font.cpp is pasted into the CFont stub below
// (renamed to ParseToken). Built twice, with and without FIX_BUGS.
#include "stubs.h"
#include "scenarios.h"
#define BUTTON_ICONS
/*@FIX_BUGS@*/

enum {
	BUTTON_NONE = -1, BUTTON_UP, BUTTON_DOWN, BUTTON_LEFT, BUTTON_RIGHT,
	BUTTON_CROSS, BUTTON_CIRCLE, BUTTON_SQUARE, BUTTON_TRIANGLE,
	BUTTON_L1, BUTTON_L2, BUTTON_L3, BUTTON_R1, BUTTON_R2, BUTTON_R3,
	BUTTON_RSTICK_UP, BUTTON_RSTICK_DOWN, BUTTON_RSTICK_LEFT, BUTTON_RSTICK_RIGHT,
	MAX_BUTTON_ICONS
};
struct CFontDetails { CRGBA color; bool anonymous_23 = false; };
struct CFont {
	CFontDetails Details;
	int PS2Symbol = BUTTON_NONE;
/*@PARSE_TOKEN@*/
};

static CFont GreyFont() {
	CFont font;
	font.Details.color.r = 175; font.Details.color.g = 175; font.Details.color.b = 175;
	return font;
}

// "~w~~h~abc" - two adjacent pure-color tokens then real text.
// With the fix, ParseToken must skip BOTH tokens in one call and
// land on 'a', not on the second token's opening '~'.
static void adjacent_color_tokens_consumed_without_literal_tilde() {
	CFont font = GreyFont();
	CRGBA color = font.Details.color;
	bool flash = false, bold = false;
	wchar str[] = { '~','w','~','~','h','~','a','b','c','\0' };
	wchar *s = font.ParseToken(str, color, flash, bold);
	assert(*s == 'a');
	assert(color.r == 255 && color.g == 255 && color.b == 255); // ~h~ applied
	assert(font.PS2Symbol == BUTTON_NONE);
}

// "~w~~T~abc" mirrors the real garble: a color token immediately
// followed by a button-icon token (the 'T' in "TOUCH..." was
// misparsed as a literal ~T~ triangle-icon token before the fix).
static void adjacent_token_then_button_icon_fires_correctly() {
	CFont font = GreyFont();
	CRGBA color = font.Details.color;
	bool flash = false, bold = false;
	wchar str[] = { '~','w','~','~','T','~','a','b','c','\0' };
	wchar *s = font.ParseToken(str, color, flash, bold);
	assert(*s == 'a');
	assert(font.PS2Symbol == BUTTON_TRIANGLE);
}

// Documents the pre-fix (FIX_BUGS undefined) behavior: ParseToken
// returns a pointer to the second token's opening '~' instead of
// skipping past it, which is what causes RenderFontBuffer to print
// a literal '~' and misfire a button icon from the following text.
static void without_fix_bugs_desyncs_on_adjacent_tokens() {
	CFont font = GreyFont();
	CRGBA color = font.Details.color;
	bool flash = false, bold = false;
	wchar str[] = { '~','w','~','~','h','~','a','b','c','\0' };
	wchar *s = font.ParseToken(str, color, flash, bold);
	assert(*s == '~'); // desync: lands on the second token's delimiter, not 'a'
}

int main(int argc, char **argv) {
	SCENARIOS_BEGIN
	SCENARIO(adjacent_color_tokens_consumed_without_literal_tilde)
	SCENARIO(adjacent_token_then_button_icon_fires_correctly)
	SCENARIO(without_fix_bugs_desyncs_on_adjacent_tokens)
	SCENARIOS_END
}
