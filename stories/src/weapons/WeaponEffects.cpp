#include "common.h"

#include "main.h"
#include "WeaponEffects.h"
#include "TxdStore.h"
#include "Sprite.h"
#include "PlayerPed.h"
#include "World.h"
#include "WeaponType.h"

RwTexture *gpCrossHairTex;

CWeaponEffects gCrossHair;

CWeaponEffects::CWeaponEffects()
{
	
}

CWeaponEffects::~CWeaponEffects()
{
	
}

void
CWeaponEffects::Init(void)
{
	gCrossHair.m_bActive = false;
	gCrossHair.m_vecPos = CVector(0.0f, 0.0f, 0.0f);
	gCrossHair.m_nRed = 255;
	gCrossHair.m_nGreen = 0;
	gCrossHair.m_nBlue = 0;
	gCrossHair.m_nAlpha = 225;
	gCrossHair.m_fSize = 1.0f;
	gCrossHair.m_fRotation = 0.0f;
	gCrossHair.m_pTarget = nil;
	gCrossHair.m_fHealthRatio = 1.0f;

	CTxdStore::PushCurrentTxd();
	int32 slot = CTxdStore::FindTxdSlot("particle");
	CTxdStore::SetCurrentTxd(slot);

	gpCrossHairTex = RwTextureRead("triangle16", nil);

	CTxdStore::PopCurrentTxd();
}

void
CWeaponEffects::Shutdown(void)
{
	RwTextureDestroy(gpCrossHairTex);
	gpCrossHairTex = nil;
}

void
CWeaponEffects::MarkTarget(CVector pos, uint8 red, uint8 green, uint8 blue, uint8 alpha, CEntity *target, float size)
{
	if (target == nil || target == gCrossHair.m_pTarget)
		return;

	if (gCrossHair.m_pTarget)
		gCrossHair.m_pTarget->CleanUpOldReference(&gCrossHair.m_pTarget);
	gCrossHair.m_pTarget = target;
	target->RegisterReference(&gCrossHair.m_pTarget);

	gCrossHair.m_bActive = true;
	gCrossHair.m_vecPos = pos;
	gCrossHair.m_fSize = size;
	gCrossHair.m_fRotation = 0.0f;

	if (target->IsPed()) {
		CPed *targetPed = (CPed*)target;
		red = 0;
		green = 255;
		blue = 0;
		alpha = 225;
		gCrossHair.m_fHealthRatio = Max(targetPed->m_fHealth / targetPed->m_fMaxHealth, 0.0f);
	} else {
		gCrossHair.m_fHealthRatio = 1.0f;
	}

	gCrossHair.m_nRed = red;
	gCrossHair.m_nGreen = green;
	gCrossHair.m_nBlue = blue;
	gCrossHair.m_nAlpha = alpha;
}

void
CWeaponEffects::ClearCrossHair(void)
{
	gCrossHair.m_bActive = false;
	if (gCrossHair.m_pTarget) {
		gCrossHair.m_pTarget->CleanUpOldReference(&gCrossHair.m_pTarget);
		gCrossHair.m_pTarget = nil;
	}
}

void
CWeaponEffects::Render(void)
{
	if (gCrossHair.m_bActive && gCrossHair.m_pTarget)
	{
		CEntity *target = gCrossHair.m_pTarget;
		CVector pos = target->GetPosition();
		float newZ;
		float liveRatio;

		if (target->IsPed()) {
			CPed *targetPed = (CPed*)target;
			RwV3d component;
			targetPed->m_pedIK.GetComponentPosition(component, PED_MID);
			newZ = component.z;
			liveRatio = Max(targetPed->m_fHealth / targetPed->m_fMaxHealth, 0.0f);
		} else if (target->IsVehicle()) {
			CRect rect = target->GetBoundRect();
			newZ = pos.z - (rect.top - rect.bottom) * 0.33f;
			liveRatio = 1.0f;
		} else {
			newZ = pos.z;
			liveRatio = 1.0f;
		}

		pos.z = (newZ + gCrossHair.m_vecPos.z) * 0.5f;
		gCrossHair.m_vecPos = pos;

		if (liveRatio < gCrossHair.m_fHealthRatio)
			gCrossHair.m_fHealthRatio = Max(gCrossHair.m_fHealthRatio - 0.1f, 0.0f);

		uint8 r = (uint8)(gCrossHair.m_nRed * gCrossHair.m_fHealthRatio);
		uint8 g = (uint8)(gCrossHair.m_nGreen * gCrossHair.m_fHealthRatio);
		uint8 b = (uint8)(gCrossHair.m_nBlue * gCrossHair.m_fHealthRatio);

		RwRenderStateSet(rwRENDERSTATEZWRITEENABLE,      (void *)FALSE);
		RwRenderStateSet(rwRENDERSTATEZTESTENABLE,       (void *)FALSE);
		RwRenderStateSet(rwRENDERSTATEVERTEXALPHAENABLE, (void *)TRUE);
		RwRenderStateSet(rwRENDERSTATESRCBLEND,          (void *)rwBLENDSRCALPHA);
#ifdef FIX_BUGS
		RwRenderStateSet(rwRENDERSTATEDESTBLEND,         (void *)rwBLENDINVSRCALPHA);
#else
		RwRenderStateSet(rwRENDERSTATEDESTBLEND,         (void *)rwBLENDINVDESTALPHA);
#endif
		RwRenderStateSet(rwRENDERSTATETEXTURERASTER,     (void *)RwTextureGetRaster(gpCrossHairTex));

		RwV3d scr;
		float w, h;
		if ( CSprite::CalcScreenCoors(gCrossHair.m_vecPos, &scr, &w, &h, true) )
		{
			PUSH_RENDERGROUP("CWeaponEffects::Render");

			float recipz = 1.0f / scr.z;
			float sw = 10.0f - Max(80.0f - h, 0.0f) * 0.08f;
			float sh = 0.8f * (10.0f - Max(80.0f - w, 0.0f) * 0.08f);

			CSprite::RenderOneXLUSprite_Rotate_Aspect(scr.x - 0.4f*w, scr.y - 0.2f*h, scr.z,
				sw, sh, r, g, b, 158, recipz, -0.8f, gCrossHair.m_nAlpha);
			CSprite::RenderOneXLUSprite_Rotate_Aspect(scr.x + 0.4f*w, scr.y - 0.2f*h, scr.z,
				sw, sh, r, g, b, 158, recipz, PI + 0.8f, gCrossHair.m_nAlpha);
			CSprite::RenderOneXLUSprite_Rotate_Aspect(scr.x, scr.y + 0.5f*h, scr.z,
				sw, sh, r, g, b, 158, recipz, HALFPI, gCrossHair.m_nAlpha);

			POP_RENDERGROUP();
		}

		RwRenderStateSet(rwRENDERSTATEVERTEXALPHAENABLE, (void *)FALSE);
		RwRenderStateSet(rwRENDERSTATEZWRITEENABLE,      (void *)TRUE);
		RwRenderStateSet(rwRENDERSTATEZTESTENABLE,       (void *)TRUE);
	}
}
