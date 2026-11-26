// Harness for test_music_frontend_track_race.py. The real cMusicManager
// declaration (stories/src/audio/MusicManager.h) and its Service,
// ServiceFrontEndMode, ChangeMusicMode and PlayFrontEndTrack bodies
// (MusicManager.cpp) are pasted in at the markers. The sample manager is a
// fake with one stream that plays from the moment it is started.
#include "stubs.h"
#include "scenarios.h"

typedef uint8 bool8;
#define TRUE 1
#define FALSE 0
#define MAX_VOLUME 127
#define VALIDATE_SIZE(struc, size)
// The game's Min is a macro (common.h) and accepts mixed types.
template<class A, class B> static inline auto Min(A a, B b) -> decltype(a < b ? a : b) { return a < b ? a : b; }
#define _3DS
#define FIX_BUGS

/*@ENUMS@*/

/*@HEADER@*/

struct FakeSampleManager {
	bool playing;
	uint32 lastStarted;
	bool8 loopFlag;
	bool8 startedLoopFlag;
	int startCount;

	bool8 IsStreamPlaying() { return playing; }
	void StopStreamedFile() { playing = false; }
	bool8 StartStreamedFile(uint32 track, uint32) {
		playing = true;
		lastStarted = track;
		startedLoopFlag = loopFlag;
		startCount++;
		return TRUE;
	}
	void SetStreamedFileLoopFlag(bool8 flag) { loopFlag = flag; }
	void SetStreamedVolumeAndPan(uint8, uint8, bool8) {}
	int32 GetStreamedFilePosition() { return 0; }
	void PauseStream(bool8) {}
} SampleManager;

struct FakeAudioManager {
	uint32 m_FrameCounter;
	bool8 m_bIsPaused;
	bool8 m_bWasPaused;
} AudioManager;

struct CTimer {
	static uint32 GetTimeInMillisecondsPauseMode() { return 0; }
};

cMusicManager MusicManager;
int32 gNumRetunePresses;
int32 gRetuneCounter;
bool8 g_bAnnouncementReadPosAlready;
static bool8 gGameStreamPausedForMenu3DS;
static int gGameModeServices;

cMusicManager::cMusicManager() { memset((void *)this, 0, sizeof(*this)); }
void cMusicManager::RecordRadioStats() {}
uint32 cMusicManager::GetTrackStartPos(uint32) { return 0; }

// During the credits the final-mission radio lock is on. ServiceGameMode then
// stops the stream and drops the frontend track (MusicManager.cpp).
void cMusicManager::ServiceGameMode()
{
	gGameModeServices++;
	SampleManager.StopStreamedFile();
	m_nPlayingTrack = NO_TRACK;
	m_nFrontendTrack = NO_TRACK;
}

/*@FUNCTIONS@*/

static cMusicManager &mm = MusicManager;

// One game frame: the script work has run, now the audio service runs.
static void frame() {
	mm.Service();
	AudioManager.m_FrameCounter++;
}

static void frames(int n) {
	for (int i = 0; i < n; i++)
		frame();
}

// State after PLAY_MISSION_PASSED_TUNE: frontend mode, jingle playing.
static void jinglePlaying() {
	mm.m_bIsInitialised = TRUE;
	mm.m_nMusicMode = mm.m_nUpcomingMusicMode = MUSICMODE_GAME;
	mm.m_nFrontendTrack = mm.m_nPlayingTrack = mm.m_nNextTrack = NO_TRACK;
	AudioManager.m_FrameCounter = 0;
	mm.ChangeMusicMode(MUSICMODE_FRONTEND);
	mm.PlayFrontEndTrack(STREAMED_SOUND_MISSION_COMPLETED, FALSE);
	frames(12);
	assert(mm.m_nMusicMode == MUSICMODE_FRONTEND);
	assert(mm.m_nPlayingTrack == STREAMED_SOUND_MISSION_COMPLETED);
	assert(SampleManager.playing && SampleManager.lastStarted == STREAMED_SOUND_MISSION_COMPLETED);
	SampleManager.startCount = 0;
	gGameModeServices = 0;
}

static void playEndOfGameTune() {
	mm.ChangeMusicMode(MUSICMODE_FRONTEND);
	mm.PlayFrontEndTrack(STREAMED_SOUND_CUTSCENE_FINALE, TRUE);
}

static void assertFinalePlaying() {
	frames(16);
	assert(mm.m_nMusicMode == MUSICMODE_FRONTEND);
	assert(mm.m_nFrontendTrack == STREAMED_SOUND_CUTSCENE_FINALE);
	assert(mm.m_nPlayingTrack == STREAMED_SOUND_CUTSCENE_FINALE);
	assert(SampleManager.playing && SampleManager.lastStarted == STREAMED_SOUND_CUTSCENE_FINALE);
	assert(SampleManager.startedLoopFlag == TRUE);
	assert(gGameModeServices == 0);
}

// SALH5 camera shot 0: SWITCH_CAR_RADIO 1, WAIT 0, then PLAY_END_OF_GAME_TUNE.
static void finale_survives_reverted_switch_to_game() {
	jinglePlaying();
	mm.ChangeMusicMode(MUSICMODE_GAME);
	frame();
	assert(mm.m_bMusicModeChangeStarted);
	playEndOfGameTune();
	assertFinalePlaying();
}

// Other camera shots: both requests in the same frame.
static void same_frame_switch_plays_finale() {
	jinglePlaying();
	mm.ChangeMusicMode(MUSICMODE_GAME);
	playEndOfGameTune();
	assertFinalePlaying();
}

// The jingle ends, ServiceFrontEndMode asks for game mode, the next pass
// latches that switch, then the end tune is requested.
static void finale_after_jingle_end_switch() {
	jinglePlaying();
	while (AudioManager.m_FrameCounter % 4 != 0)
		frame();
	SampleManager.playing = false;
	frame();
	assert(mm.m_nUpcomingMusicMode == MUSICMODE_GAME);
	frame();
	assert(mm.m_bMusicModeChangeStarted && mm.m_nMusicMode == MUSICMODE_FRONTEND);
	playEndOfGameTune();
	assertFinalePlaying();
}

// A switch to game mode that nobody reverses still completes and drops the
// frontend track.
static void unreversed_switch_to_game_clears_track() {
	jinglePlaying();
	mm.ChangeMusicMode(MUSICMODE_GAME);
	frame();
	mm.PlayFrontEndTrack(STREAMED_SOUND_CUTSCENE_FINALE, TRUE);
	frames(16);
	assert(mm.m_nMusicMode == MUSICMODE_GAME);
	assert(mm.m_nFrontendTrack == NO_TRACK);
	assert(SampleManager.startCount == 0);
	assert(gGameModeServices > 0);
}

int main(int argc, char **argv) {
	SCENARIOS_BEGIN
	SCENARIO(finale_survives_reverted_switch_to_game)
	SCENARIO(same_frame_switch_plays_finale)
	SCENARIO(finale_after_jingle_end_switch)
	SCENARIO(unreversed_switch_to_game_clears_track)
	SCENARIOS_END
}
