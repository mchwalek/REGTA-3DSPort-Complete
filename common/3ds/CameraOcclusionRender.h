#pragma once
#ifdef _3DS
#include "CameraOcclusion.h"
namespace CameraOcclusion3DS
{
struct RenderScope {
	rw::c3d::EntityRenderStyle previous;
	uint32 zwrite;
	bool changed;
	RenderScope(CEntity *entity) : previous(rw::c3d::getEntityRenderStyle()), zwrite(0), changed(false)
	{
		auto style = previous;
		// Unlit 3DS paths ignore the scorched lighting set by SetupLighting.
		style.scorched = entity->bRenderScorched;
		const float alpha = Alpha(entity);
		if(alpha < 1.f) {
			if(style.opacity > alpha) style.opacity = alpha;
			zwrite = rw::GetRenderState(rw::ZWRITEENABLE);
			rw::SetRenderState(rw::ZWRITEENABLE, 0);
			changed = true;
		}
		rw::c3d::setEntityRenderStyle(style);
	}
	~RenderScope()
	{
		rw::c3d::setEntityRenderStyle(previous);
		if(changed)
			rw::SetRenderState(rw::ZWRITEENABLE, zwrite);
	}
};
} // namespace CameraOcclusion3DS
#endif
