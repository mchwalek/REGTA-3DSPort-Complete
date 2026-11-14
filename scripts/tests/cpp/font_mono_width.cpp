// Harness for test_font_mono_width.py: the real CFont width functions from
// stories/src/renderer/Font.cpp (IsPunctuation, GetCharacterWidth,
// GetCharacterSize, GetStringWidth and the Size table) pasted against stubs.
#include "stubs.h"
#include "scenarios.h"

enum { FONT_BANK, FONT_STANDARD, FONT_HEADING, MAX_FONTS };

struct CFontDetails {
	float scaleX;
	bool proportional;
	bool bFontHalfTexture;
	int16 style;
};
struct CFontRenderState {
	float scaleX;
	bool proportional;
	int16 style;
};
struct CFont {
	static CFontDetails Details;
	static CFontRenderState RenderState;
	static int16 Size[MAX_FONTS][419];
	static wchar FindNewCharacter(wchar c) { return c; }
	static float GetCharacterWidth(wchar c, bool forceProportional = false);
	static float GetCharacterSize(wchar c);
	static float GetStringWidth(wchar *s, bool spaces = false);
};
CFontDetails CFont::Details;
CFontRenderState CFont::RenderState;

/*@SIZE_TABLE@*/
/*@IS_PUNCTUATION@*/
/*@WIDTH_FUNCS@*/

static void Use(bool proportional, float scaleX) {
	CFont::Details.style = CFont::RenderState.style = FONT_STANDARD;
	CFont::Details.proportional = CFont::RenderState.proportional = proportional;
	CFont::Details.scaleX = CFont::RenderState.scaleX = scaleX;
	CFont::Details.bFontHalfTexture = false;
}

// RenderFontBuffer advances each glyph by RenderState.scaleX * GetCharacterWidth(c);
// PrintString right-justifies with GetStringWidth. They must agree, or
// right-aligned HUD text (mission timer/counters) ends short of its anchor.
static float RenderedWidth(const wchar *s) {
	float w = 0.0f;
	for (; *s; s++)
		w += CFont::RenderState.scaleX * CFont::GetCharacterWidth(*s - ' ');
	return w;
}

static void check(bool proportional) {
	// no punctuation: PS2 itself scales the incrementer by 1/1.6 in one of the two (0x1670a8 vs 0x167250)
	wchar s[] = { '1', '2', '0', '9', '\0' };
	Use(proportional, 0.337f);
	float layout = CFont::GetStringWidth(s);
	float render = RenderedWidth(s);
	assert(layout > render - 0.001f && layout < render + 0.001f);
}

static void monospace_layout_width_matches_render() { check(false); }
static void proportional_layout_width_matches_render() { check(true); }

int main(int argc, char **argv) {
	SCENARIOS_BEGIN
	SCENARIO(monospace_layout_width_matches_render)
	SCENARIO(proportional_layout_width_matches_render)
	SCENARIOS_END
}
