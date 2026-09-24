#pragma once

class CEntity;

class CWeaponEffects
{
public:
	bool m_bActive;
	CVector m_vecPos;
	uint8 m_nRed;    // base colour (pre-health-ratio scaling)
	uint8 m_nGreen;
	uint8 m_nBlue;
	uint8 m_nAlpha;
	float m_fSize;
	float m_fRotation;
	CEntity *m_pTarget;
	float m_fHealthRatio;

public:
	CWeaponEffects();
	~CWeaponEffects();

	static void Init(void);
	static void Shutdown(void);
	static void MarkTarget(CVector pos, uint8 red, uint8 green, uint8 blue, uint8 alpha, CEntity *target, float size);
	static void ClearCrossHair(void);
	static void Render(void);
};
