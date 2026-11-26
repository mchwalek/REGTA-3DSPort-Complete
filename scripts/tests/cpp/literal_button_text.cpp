// Harness for test_3ds_literal_button_text.py: Replace3DSLiteralButtonText
// from stories/src/text/Text.cpp is pasted in at the marker below.
#include "stubs.h"

#define ARRAY_SIZE(a) (sizeof(a) / sizeof((a)[0]))

/*@FUNCTION@*/

static wchar wbuf[4][512];
static int wnext;

static wchar *W(const char *s)
{
	wchar *out = wbuf[wnext++ & 3];
	uint32 i = 0;
	for (; s[i]; i++)
		out[i] = (uint8)s[i];
	out[i] = 0;
	return out;
}

static bool Equal(const wchar *a, const char *b)
{
	for (; *a && *b; a++, b++)
		if (*a != (uint8)*b)
			return false;
	return *a == 0 && *b == 0;
}

static void check(const char *key, const char *in, const char *expected)
{
	wchar *out = Replace3DSLiteralButtonText(key, W(in));
	if (!Equal(out, expected)) {
		fprintf(stderr, "%s: \"%s\" did not become \"%s\"\n", key, in, expected);
		assert(false);
	}
}

int main()
{
	check("TUP_AD", "~w~You have 3 adrenaline pills, Press R1 button to use one.",
	      "~w~You have 3 adrenaline pills, Press R button to use one.");
	check("TUP_AD", "Appuie sur la touche R1 pour en utiliser une.", "Appuie sur la touche R pour en utiliser une.");
	check("TUP_AD", "Druecke die R1-Taste, um eine zu nehmen.", "Druecke die R-Taste, um eine zu nehmen.");
	check("TUP_AD", "premi il tasto R1 per usarne una.", "premi il tasto R per usarne una.");
	check("TUP_AD", "Pulsa el boton R1 para usar una.", "Pulsa el boton R para usar una.");
	check("TUP_AD", "R1", "R");
	check("TUP_AD", "R10 AR1 xR1y", "R10 AR1 xR1y");
	check("TUP_AD", "no button here", "no button here");

	// Keys outside the table come back as the same pointer.
	wchar *other = W("Press R1 button");
	assert(Replace3DSLiteralButtonText("KE_ADR", other) == other);
	assert(Replace3DSLiteralButtonText("TUP_AD", nil) == nil);

	// A string longer than the buffer is truncated and stays terminated.
	char longText[301];
	memset(longText, 'a', 300);
	longText[300] = 0;
	wchar *out = Replace3DSLiteralButtonText("TUP_AD", W(longText));
	uint32 len = 0;
	while (out[len])
		len++;
	assert(len > 0 && len < 300);
	return 0;
}
