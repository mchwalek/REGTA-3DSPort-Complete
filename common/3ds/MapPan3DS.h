#pragma once
#ifdef _3DS
namespace MapPan3DS
{
inline float
Bound(float x, float lo, float hi)
{
	return x < lo ? lo : (x > hi ? hi : x);
}
// PS2 pause-menu map panning on one axis (SLES_541.35 0x33f578): the map
// scrolls under a centred crosshair until its edge reaches the screen edge,
// then the crosshair itself moves. Moving back snaps it to the centre first.
// move: how far the crosshair travels over the map this frame (screen units).
// offset: crosshair - screenCentre. center: map centre, kept within
// screenCentre +- limit.
inline void
Pan(float move, float &offset, float &center, float screenCentre, float limit, float halfScreen)
{
	if(offset != 0.0f && limit > 0.0f && (offset > 0.0f) != (offset + move > 0.0f)) {
		move += offset;
		offset = 0.0f;
	}
	if(offset == 0.0f) {
		float c = Bound(center - move, screenCentre - limit, screenCentre + limit);
		// exact zero unless the map hit its edge, so float noise can't nudge the crosshair
		move = c == center - move ? 0.0f : move - (center - c);
		center = c;
	}
	offset = Bound(offset + move, -halfScreen, halfScreen);
}
}
#endif
