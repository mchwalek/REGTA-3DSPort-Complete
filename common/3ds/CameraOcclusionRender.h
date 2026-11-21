#pragma once
#ifdef _3DS
#include "CameraOcclusion.h"
#ifdef RESTORIES_3DS_BUILD
#include "Object.h"
#endif
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
#ifdef RESTORIES_3DS_BUILD
		// LCS PS2 building pipe: prelight scaled by timecycle ambient.
		style.leedsBuildingLighting = entity->IsBuilding();
		// PS2 ped/car lighting for the unlit skin and MatFX paint paths. Cutscene
		// actors are lit like peds (CCutsceneObject::SetupLighting); other objects are not.
		style.leedsEntityLighting = entity->IsPed() || entity->IsVehicle() ||
			(entity->IsObject() && ((CObject*)entity)->ObjectCreatedBy == CUTSCENE_OBJECT);
#endif
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
