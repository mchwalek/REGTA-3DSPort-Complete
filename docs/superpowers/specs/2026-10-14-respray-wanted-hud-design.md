# Respray wanted-level HUD grace period (3DS) — Design

## Bug report

Visiting a Pay 'n' Spray appears to clear the wanted level immediately,
instead of keeping a grace period (as in Vice City) during which committing
a new crime restores the old wanted level.

## Root cause

The underlying game mechanics already match PS2 LCS and Vice City. Verified
via PS2 (`SLUS_214.23`) disassembly of the respray's `CGarage::Update`
`GS_FULLYCLOSED` case and `CWanted::Update`/`CWanted::Suspend` (identical in
`stories/src/core/Wanted.cpp`, `miami/src/core/Wanted.cpp`, and inlined in
PS2's garage code):

- Respray sets `m_nWantedLevel`/`m_nChaos` to 0 immediately.
- The old level is preserved as `m_nMinWantedLevel`/`m_nMinChaos` for 20
  seconds (`m_nLastTimeSuspended + 20000`, `stories/src/core/Wanted.cpp:402`).
- Any crime committed within those 20 seconds (`CWanted::RegisterCrime`,
  `Wanted.cpp:305`) does `m_nChaos = Max(m_nChaos, m_nMinChaos)`, restoring
  the old wanted level.

This is exactly the Vice City behavior the bug report asks for. The bug is
purely a 3DS HUD display issue: the flashing "suspended" stars that
communicate this grace period to the player never draw on 3DS, making it
*look* like the wanted level was wiped for good.

The suppression is in `stories/src/renderer/Hud.cpp:739-743`:

```cpp
if (m_WantedState != FADED_OUT
#ifdef ENABLE_3DS_BOTTOM_RADAR
    && playerPed->m_pWanted->GetWantedLevel() > 0
#endif
```

When `GetWantedLevel() == 0` (true immediately after a respray), the entire
star-drawing block is skipped on 3DS builds — including the branch that
draws the grace-period indicator (`Hud.cpp:765-766`:
`m_nMinWantedLevel > i && FRAMECOUNTER & 4` → flashing blue star,
`CRGBA(62,141,188,alpha)`).

The non-3DS font-rendering path (`Hud.cpp:771-779`) has no such gate and is
unaffected.

## Why the gate exists (and can't just be removed)

Under `ENABLE_3DS_BOTTOM_RADAR`, the 3DS sprite path draws all 6 star slots
unconditionally whenever the block runs — 0 wanted stars would otherwise
render as 6 dim placeholder stars (`CRGBA(70,58,34)`) all the time. The gate
exists to hide that placeholder row entirely when there's nothing to show.

## Fix

Widen the gate to also run while a grace period is active:

```cpp
&& (playerPed->m_pWanted->GetWantedLevel() > 0 || playerPed->m_pWanted->m_nMinWantedLevel > 0)
```

Effect:
- Immediately after a respray, `m_nMinWantedLevel` still holds the old
  level, so the block runs and the flashing blue grace-period stars render,
  same as other platforms.
- Once `CWanted::Update` expires the grace period after 20s
  (`m_nMinWantedLevel = 0`), the condition goes false again and stars
  disappear as before.
- No change to `m_WantedState`/fade logic (`DrawFadeState`,
  `Hud.cpp:2377`), which already fades correctly on level transitions.

Scope: `stories/src/renderer/Hud.cpp` only. `miami/src/render/Hud.cpp` has
an identical gate (`Hud.cpp:720-723`) but is out of scope per the bug
report (LCS/3DS only) — note this explicitly in the commit message so it
isn't mistaken for an oversight.

## Non-goals

- No change to `CWanted`/`Garages.cpp` mechanics — they already match PS2
  and Vice City.
- No change to the non-3DS font HUD path.
- No change to `miami/`.

## Testing

- `scripts/tests` Python suite and `scripts/verify-layout.sh` (no coverage
  of HUD drawing, but confirm nothing else broke).
- Build `scripts/build.sh relcs` and visually verify on-device/emulator:
  1. Get 2+ wanted stars, respray at a Pay 'n' Spray.
  2. Confirm flashing blue stars show for ~20s after the respray.
  3. Confirm committing a crime during that window restores the prior
     wanted level and stars stop flashing (now solid).
  4. Confirm stars disappear after ~20s if no crime is committed.

No new automated test is added — this is a single display condition with
no unit-testable logic, and HUD rendering isn't covered by the existing
Python test suite.
