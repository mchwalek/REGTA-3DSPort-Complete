# AI melee attack gate: police never swing the nightstick at the player

## Bug

At 1 star a street cop switches to his nightstick (`CopPed.cpp` `CopAI`),
runs up to the player, then stands about 2 m away facing him and never
swings. Because the cop never knocks the player down, the arrest path in
`CPed::KillCharOnFootMelee` (`dist < 1.5` while the player is getting up or
being dragged from a car) never fires either.

The same bug affects every AI ped using a non-fist melee weapon against the
player: cops with nightsticks, gang members with bats or knives, and mission
characters.

## Root cause

Commit `4c7c4f4` ("port PS2's AI melee approach spacing") added a branch to
`CPed::KillCharOnFootMelee` (`stories/src/peds/PedAI.cpp`) for weapons other
than fists and brass knuckles. It seeks the victim's position and keeps
`max(0.4 * wepRange, 0.8)` away, skipping `FindMeleeAttackPoint`.

That branch never sets `canReachVictim`. The attack gate inherited from reVC
is:

```cpp
if (canReachVictim || !victimPlayer) {
	SetMoveState(PEDMOVE_STILL);
	SetAttack(m_pedInObjective);
	...
}
return ATTACK_IN_PROGRESS;
```

For a non-fist melee weapon against the player, `canReachVictim` is false and
`victimPlayer` is non-nil, so `SetAttack` is unreachable. In reVC `canReachVictim`
was always set by the `FindMeleeAttackPoint` path for any player within 5 m,
which is why `miami/` works.

## PS2 reference (`SLES_541.35`)

PS2 `KillCharOnFootMelee` spans roughly VA `0x31e0b0`-`0x31e860`.

- **Non-fist melee approach** (`0x31e1a4`-`0x31e23c`): weapon types 2-11
  seek the victim's position and keep `0.4 * range` (min `0.8`) away.
  Already matched by reLCS.
- **Arrest** (`0x31e348`-`0x31e3e4`): 1.5 m, only while the player is
  getting up or being dragged from a car. Already matched by reLCS; the 2.0 m
  nightstick stand-off is also PS2's, so it needs no change.
- **Attack gate** (`0x31e51c`-`0x31e60c`): if `dist < wepRange`, the attack
  timer has elapsed, and the victim is not `PED_GETUP` / `PED_DRAG_FROM_CAR`,
  PS2 calls `SetMoveState(STILL)`, `SetAttack(victim)`, turns toward the
  victim and sets the shoot/attack timers. There is no reachability
  condition.

## Fix

`stories/src/peds/PedAI.cpp`, in `KillCharOnFootMelee`'s attack gate:

```cpp
if (canReachVictim || !victimPlayer || !isUnarmedOrBrassKnuckle) {
```

- Non-fist melee weapons always pass the gate, matching PS2.
- Fist/brass-knuckle behaviour is unchanged (still reVC's attack-point
  logic; a separate PS2 difference, out of scope).
- The approach is unchanged: `canReachVictim` stays false for non-fist
  weapons, so the seek still targets the victim ped rather than a snapshot of
  the victim's position. Setting `canReachVictim = true` in the non-fist branch
  was rejected because it would also change the seek
  (`SetSeek(m_vecSeekPos, ...)` and skip the path-node seek), which PS2 does
  not do.
- `III/` and `miami/` do not have the non-fist branch, so only `stories/`
  changes.

## Testing

- `scripts/tests/test_ai_melee_attack_gate.py`: extracts the body of
  `CPed::KillCharOnFootMelee` from `stories/src/peds/PedAI.cpp` and asserts
  that the condition guarding `SetAttack(m_pedInObjective)` lets non-fist
  melee weapons through (it references `isUnarmedOrBrassKnuckle` negated, not
  only `canReachVictim || !victimPlayer`). The function depends on too much
  of the engine to compile in isolation, so this is a source-level check.
- `python3 -m unittest discover -s scripts/tests -p 'test_*.py'`
- `scripts/build.sh relcs`
- On device: get 1 star and stand still near a street cop. The cop should
  swing the nightstick, knock the player down, and arrest him. Also check a
  bat-wielding gang member attacks when provoked.
