#ifndef FOJ_BATTLE_REPLAY_H
#define FOJ_BATTLE_REPLAY_H

/* Synthetic 8x6 battle only: compact, bounded host/Switch command history.
 * Never consumes game files and never logs original PS3 assets. */
#include "tactical_battle.h"

#include <stdbool.h>
#include <stdint.h>

enum { FOJ_REPLAY_MAX_INPUTS = 128 };

typedef enum {
    FOJ_REPLAY_UP = 0,
    FOJ_REPLAY_DOWN,
    FOJ_REPLAY_LEFT,
    FOJ_REPLAY_RIGHT,
    FOJ_REPLAY_A,
    FOJ_REPLAY_B,
    FOJ_REPLAY_X,
    FOJ_REPLAY_ZR,
    FOJ_REPLAY_Y,
    FOJ_REPLAY_RESET,
    FOJ_REPLAY_COMMAND_COUNT
} FojReplayCommand;

typedef struct {
    uint16_t count;
    uint8_t commands[FOJ_REPLAY_MAX_INPUTS];
} FojBattleReplay;

void foj_replay_init(FojBattleReplay *log);

/* Record a real controller action ONLY if the log has room. Accepted
 * commands record even when tactical rules reject them, so replaying
 * an exact user input history reproduces terminal and invalid buttons.
 * Return false for bad pointer, illegal command or a full log, and
 * never change the battle in these failure cases. */
bool foj_replay_record(FojBattleReplay *log, FojBattle *battle,
                       FojReplayCommand command, FojBattleEvent *event);

/* Reconstruct from the same synthetic initial battle and replay input
 * order, then compare the complete deterministic state byte-for-byte.
 * No external files, RNG, timestamps, wall clock or allocation. */
bool foj_replay_reconstruct(const FojBattleReplay *log,
                            FojBattle *reconstructed);
bool foj_replay_matches(const FojBattleReplay *log,
                         const FojBattle *live);

#endif
