// Harness for test_3ds_fire_particle_budget.py: the RW_3DS pool define and
// the _3DS particle admission code from stories/src/renderer/Particle.cpp
// are pasted in at the markers below.
#include <cassert>
#include "scenarios.h"
#define nil nullptr
#define ARRAY_SIZE(array) (sizeof(array) / sizeof(array[0]))
enum tParticleType { PARTICLE_SPARK, PARTICLE_FLAME, PARTICLE_FIREBALL, PARTICLE_CARFLAME,
	PARTICLE_SMOKE, PARTICLE_CARFLAME_SMOKE, PARTICLE_FIREBALL_SMOKE, PARTICLE_EXPLOSION_LARGE, NUM_TYPES };
static bool stereo;
namespace EffectBudget3DS { inline int Limit(int capacity) { return stereo ? capacity / 2 : capacity; } }

struct CParticle;
struct tParticleSystemData { CParticle *m_pParticles; };
static struct { tParticleSystemData m_aParticles[NUM_TYPES]; } mod_ParticleSystemManager;
struct CParticle {
	CParticle *m_pNext;
	int age;
	static void RemoveParticle(CParticle *p, CParticle *prev, tParticleSystemData *psystem);
};

/*@DEFINES@*/
/*@BUDGET@*/

// Same unlink + count as the real RemoveParticle; freed slots are not reused here.
void CParticle::RemoveParticle(CParticle *p, CParticle *prev, tParticleSystemData *psystem) {
	if(prev) prev->m_pNext = p->m_pNext;
	else psystem->m_pParticles = p->m_pNext;
	--nActiveParticles3DS;
	p->m_pNext = nil;
}

static CParticle pool[4096];
static int used, clock;

// Mirrors AddParticle: admit, then head-insert into the type's list.
static int add(tParticleType type, int wanted) {
	int added = 0;
	for(; added < wanted && ParticleAdmit3DS(type); added++) {
		CParticle *p = &pool[used++];
		p->age = clock++;
		p->m_pNext = mod_ParticleSystemManager.m_aParticles[type].m_pParticles;
		mod_ParticleSystemManager.m_aParticles[type].m_pParticles = p;
		++nActiveParticles3DS;
	}
	return added;
}

static int count(tParticleType type) {
	int n = 0;
	for(CParticle *p = mod_ParticleSystemManager.m_aParticles[type].m_pParticles; p; p = p->m_pNext) n++;
	return n;
}

static int oldestAge(tParticleType type) {
	CParticle *p = mod_ParticleSystemManager.m_aParticles[type].m_pParticles;
	while(p->m_pNext) p = p->m_pNext;
	return p->age;
}

static void reset() {
	nActiveParticles3DS = used = clock = 0;
	for(auto &s : mod_ParticleSystemManager.m_aParticles) s.m_pParticles = nil;
}

static void fire_replaces_oldest_smoke() {
	reset(); stereo = false;
	assert(add(PARTICLE_FIREBALL_SMOKE, 100) == 100);
	assert(add(PARTICLE_CARFLAME_SMOKE, 1000) == MAX_PARTICLES_ON_SCREEN - 100);
	assert(add(PARTICLE_EXPLOSION_LARGE, 10) == 0);
	int firstCarflameSmoke = oldestAge(PARTICLE_CARFLAME_SMOKE);
	assert(add(PARTICLE_CARFLAME, 10) == 10);
	assert(nActiveParticles3DS == MAX_PARTICLES_ON_SCREEN);
	assert(oldestAge(PARTICLE_CARFLAME_SMOKE) == firstCarflameSmoke + 10);
	assert(count(PARTICLE_FIREBALL_SMOKE) == 100);  // fire's own smoke goes first
}

static void fire_falls_back_to_other_smoke() {
	reset(); stereo = false;
	assert(add(PARTICLE_CARFLAME_SMOKE, 5) == 5);
	assert(add(PARTICLE_SMOKE, 1000) == MAX_PARTICLES_ON_SCREEN - 5);
	assert(add(PARTICLE_FLAME, 20) == 20);
	assert(count(PARTICLE_CARFLAME_SMOKE) == 0);
	assert(count(PARTICLE_SMOKE) == MAX_PARTICLES_ON_SCREEN - 20);
}

static void fire_refused_when_no_smoke() {
	reset(); stereo = false;
	assert(add(PARTICLE_SPARK, 1000) == MAX_PARTICLES_ON_SCREEN);
	assert(add(PARTICLE_FIREBALL, 10) == 0);
	assert(count(PARTICLE_SPARK) == MAX_PARTICLES_ON_SCREEN);
}

static void flamethrower_replaces_oldest_flame() {
	reset(); stereo = false;
	assert(add(PARTICLE_FLAME, 6) == 6);
	assert(add(PARTICLE_CARFLAME, 1000) == MAX_PARTICLES_ON_SCREEN - 6);
	assert(add(PARTICLE_CARFLAME, 10) == 0);  // fires never replace each other
	assert(add(PARTICLE_FLAME, 10) == 0);
	int firstCarflame = oldestAge(PARTICLE_CARFLAME);
	assert(add(PARTICLE_FIREBALL, 5) == 5);
	assert(oldestAge(PARTICLE_CARFLAME) == firstCarflame + 5);
	assert(count(PARTICLE_FLAME) == 6);
	assert(add(PARTICLE_FIREBALL, 1000) == MAX_PARTICLES_ON_SCREEN - 5);  // then FLAME, never itself
	assert(count(PARTICLE_FIREBALL) == MAX_PARTICLES_ON_SCREEN);
	assert(nActiveParticles3DS == MAX_PARTICLES_ON_SCREEN);
}

static void stereo_halves_cap() {
	reset(); stereo = true;
	assert(add(PARTICLE_CARFLAME_SMOKE, 1000) == MAX_PARTICLES_ON_SCREEN / 2);
	assert(add(PARTICLE_CARFLAME, 1000) == MAX_PARTICLES_ON_SCREEN / 2);  // replaces all smoke, never more
	assert(nActiveParticles3DS == MAX_PARTICLES_ON_SCREEN / 2);
	assert(count(PARTICLE_CARFLAME_SMOKE) == 0);
}

int main(int argc, char **argv) {
	SCENARIOS_BEGIN
	SCENARIO(fire_replaces_oldest_smoke)
	SCENARIO(fire_falls_back_to_other_smoke)
	SCENARIO(fire_refused_when_no_smoke)
	SCENARIO(flamethrower_replaces_oldest_flame)
	SCENARIO(stereo_halves_cap)
	SCENARIOS_END
}
