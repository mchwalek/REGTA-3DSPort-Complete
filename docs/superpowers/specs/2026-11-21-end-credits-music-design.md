# End credits music (reLCS 3DS)

Trello: https://trello.com/c/PQUsNfRS "Missing music during end credits".

## Problem

After SALH5 ("Last Stand") the end credits can run in silence. The end tune
(`AUDIO/MUSIC/FINALE`, `STREAMED_SOUND_CUTSCENE_FINALE`) never starts.

## What the original does

`main.scm` (PS2 disc), SALH5 credits subroutine at `0x17a37`:

1. Mission passed block (`0x128e2a`): `PLAY_MISSION_PASSED_TUNE 1`. The
   5.4 s jingle starts in frontend music mode.
2. `WAIT 1000`, then the credits: `CALL 31629` (`SWITCH_CAR_RADIO 0`, a
   1000 ms fade out with a `WAIT 0` loop), a `WAIT 0` loop that looks for a
   random car, then `CALL 31786`, which runs `SWITCH_CAR_RADIO 1`, which is
   `ChangeMusicMode(GAME)`.
3. Camera subroutine `0x17e1c`. For a car that is not a bike it picks one of
   three shots at random. Shot 0 runs `WAIT 0` before it returns.
4. `PLAY_END_OF_GAME_TUNE` (`0x17b6e`): `ChangeMusicMode(FRONTEND)`, then
   `PlayFrontEndTrack(FINALE, loop)`.

The jingle is still playing when step 2 asks for game mode.

PS2 handlers in `SLES_541.35`: `SWITCH_CAR_RADIO` `0x227e94`,
`PLAY_END_OF_GAME_TUNE` `0x268ba8`, `ChangeMusicMode` `0x167c58`,
`PlayFrontEndTrack` `0x169e38`, `cMusicManager::Service` `0x167e80`,
`ServiceFrontEndMode` `0x1680d8`. The reLCS script handlers and these music
manager functions match PS2.

## Root cause

`cMusicManager::Service` latches a mode change (`m_bMusicModeChangeStarted`,
`m_nMusicModeToBeSet`) on the first service pass that sees a new
`m_nUpcomingMusicMode`. It completes the change on a later
every-fourth-frame pass, once the stream has stopped. At completion it
clears `m_nFrontendTrack` unless `m_bEarlyFrontendTrack` is set.
`PlayFrontEndTrack` sets that flag only when `m_nMusicMode` is not
frontend.

When the camera picks shot 0, the order is:

- Frame N: `SWITCH_CAR_RADIO 1` asks for game mode. The service latches
  frontend → game and stops the jingle.
- Frame N+1: `PLAY_END_OF_GAME_TUNE` asks for frontend mode and sets
  `m_nFrontendTrack = FINALE`. `m_nMusicMode` is still frontend, so the
  early flag stays clear.
- A few frames later the latched switch to game completes and clears
  `m_nFrontendTrack`. The manager then switches back to frontend mode with
  no track. The credits play in silence.

When the camera picks another shot, both requests arrive in the same frame
and the music plays. That makes the bug intermittent, about one run in three
for a car. The same thing happens when the jingle ends on its own
(`ServiceFrontEndMode` asks for game mode) shortly before
`PLAY_END_OF_GAME_TUNE`. PS2 has the same state machine, so this is a bug
in the original logic that the 3DS port inherits.

Ruled out while tracing:

- Script handlers: `PLAY_END_OF_GAME_TUNE`, `STOP_END_OF_GAME_TUNE`,
  `SET_MUSIC_DOES_FADE`, `SWITCH_CAR_RADIO` match PS2.
- Track data: `FINALE.WAV` is on the SD card, and the stream loops with
  `SetLoopCount(0)`.
- Music fade: `CALL 31786` starts the 1000 ms fade in before
  `SET_MUSIC_DOES_FADE 0`, and that fade is not cancelled.
- Final mission BGM: `FinalMissionMusic` uses stream 1 and only touches
  game mode service.
- Underruns: `CStream` refills and restarts its source by itself, and
  `ServiceFrontEndMode` leaves a stopped FINALE alone, so a short underrun
  does not end the tune.

## Fix

In `cMusicManager::PlayFrontEndTrack` (`stories/src/audio/MusicManager.cpp`),
under `FIX_BUGS`: if a latched switch away from frontend mode is still in
progress, the current mode is frontend, and the caller has asked for
frontend mode again, cancel the latched switch
(`m_bMusicModeChangeStarted = FALSE`). The next service pass sees frontend
as both current and requested mode. `ServiceFrontEndMode` then stops the
jingle and starts FINALE through its normal track change.

A switch to game mode that nobody reverses still completes as before, and
still clears the frontend track.

## Rulings

- Ruling: fix the race in `PlayFrontEndTrack` and leave the mode-change code
  in `Service` alone. Why: only a new frontend track request has to win over
  a pending switch, and pause-menu radio bookkeeping lives in `Service`.
  Cost if wrong: another reversed request (for example game → frontend →
  game) keeps PS2's round-trip behaviour, which is what ships today.
- Ruling: cancel the latched switch instead of letting FINALE survive a
  game → frontend round trip. Why: the round trip clears the track twice and
  would need a second flag, while cancelling leaves no window in which
  `ServiceGameMode` (which clears `m_nFrontendTrack` under the final-mission
  radio lock) can run. Cost if wrong: the function-static
  `bRadioStatsRecorded` in `Service` can stay set until the next completed
  mode change, so that change skips one radio position save. Frontend mode
  plays no radio, so nothing is lost.
- Ruling: gate the fix with `FIX_BUGS`, not `_3DS`. Why: PS2 has the same
  bug, and the repo marks fixes to original logic with `FIX_BUGS`. Cost if
  wrong: none for the 3DS build, where `FIX_BUGS` is always on.
- Ruling: do not port PS2's "RESTARTING TRACK" branch (`0x1680d8` restarts
  track `0x3f`, FINALE, from position 0 when the stream is not playing). Why:
  on 3DS `IsStreamPlaying()` is false for a frame during an underrun, which
  `CStream` recovers from by itself. A restart from 0 would turn each
  underrun into an audible restart. Cost if wrong: a FINALE stream that
  stops for good stays silent until `STOP_END_OF_GAME_TUNE`.
- Ruling: do not port PS2's `PlayFrontEndTrack` fourth argument (the
  `0x394` flag and the object at `0x3d0a84`). Why: it does not change which
  track plays and has no reLCS counterpart. Cost if wrong: none seen.

## Scope

Only `stories/` changes. III and miami have the same state machine. They are
not changed here.

## Test

`scripts/tests/test_music_frontend_track_race.py` with harness
`scripts/tests/cpp/music_frontend_track_race.cpp`. It pastes the real
`Service`, `ServiceFrontEndMode`, `ChangeMusicMode` and `PlayFrontEndTrack`
into a stub `cMusicManager` built from the real `MusicManager.h`, with a
fake `SampleManager` stream. Scenarios:

- The SALH5 shot 0 order (game request, one service, frontend request plus
  FINALE) starts FINALE with the loop flag and stays in frontend mode.
- The same-frame order still starts FINALE.
- When the jingle ends on its own, a frontend track requested after the
  automatic switch to game mode has latched, but before it completes, still
  starts FINALE.
- A switch to game mode that nobody reverses still completes and clears
  the frontend track.

Without the fix, the first and third scenarios fail.
