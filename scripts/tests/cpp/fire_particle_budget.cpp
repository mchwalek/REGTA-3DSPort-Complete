// Harness for test_3ds_fire_particle_budget.py: the RW_3DS pool defines and
// the _3DS particle admission budget from stories/src/renderer/Particle.cpp
// are pasted in at the markers below.
#include <cassert>
#include "scenarios.h"
enum tParticleType { PARTICLE_SPARK, PARTICLE_FLAME, PARTICLE_FIREBALL, PARTICLE_CARFLAME, PARTICLE_CARFLAME_SMOKE, PARTICLE_EXPLOSION_LARGE };
static bool stereo;
namespace EffectBudget3DS { inline int Limit(int capacity) { return stereo ? capacity / 2 : capacity; } }

/*@DEFINES@*/
/*@BUDGET@*/

// Mirrors AddParticle: refuse when full, otherwise count the new particle.
static int fill(tParticleType type, int wanted) {
	int added = 0;
	for(int i = 0; i < wanted && !ParticleBudgetFull3DS(type); i++, added++)
		++ParticleCounter3DS(type);
	return added;
}

static void reset() { nActiveParticles3DS = nActiveFireParticles3DS = 0; }

static void smoke_does_not_starve_fire() {
	reset(); stereo = false;
	assert(fill(PARTICLE_CARFLAME_SMOKE, 1000) == 256);
	assert(fill(PARTICLE_EXPLOSION_LARGE, 10) == 0);
	assert(fill(PARTICLE_CARFLAME, 100) == 100);
	assert(fill(PARTICLE_FIREBALL, 100) == 100);
	assert(fill(PARTICLE_FLAME, 100) == 100);
}

static void fire_shares_rest_of_ps2_pool() {
	reset(); stereo = false;
	assert(fill(PARTICLE_FIREBALL, 1000) + fill(PARTICLE_CARFLAME, 1000) == MAX_PARTICLES_ON_SCREEN - 256);
	assert(fill(PARTICLE_SPARK, 1000) + nActiveFireParticles3DS == MAX_PARTICLES_ON_SCREEN);
	--ParticleCounter3DS(PARTICLE_CARFLAME);                 // RemoveParticle frees a slot
	assert(fill(PARTICLE_CARFLAME, 10) == 1);
}

static void stereo_halves_both_budgets() {
	reset(); stereo = true;
	assert(fill(PARTICLE_CARFLAME_SMOKE, 1000) == 128);
	assert(fill(PARTICLE_CARFLAME, 1000) == (MAX_PARTICLES_ON_SCREEN - 256) / 2);
}

int main(int argc, char **argv) {
	SCENARIOS_BEGIN
	SCENARIO(smoke_does_not_starve_fire)
	SCENARIO(fire_shares_rest_of_ps2_pool)
	SCENARIO(stereo_halves_both_budgets)
	SCENARIOS_END
}
