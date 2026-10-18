#include "battle_replay.h"

#include <stddef.h>
#include <string.h>

void foj_replay_init(FojBattleReplay *log) {
    if (log) memset(log, 0, sizeof(*log));
}

static FojBattleEvent execute_command(FojBattle *battle,
                                      FojReplayCommand command) {
    switch (command) {
        case FOJ_REPLAY_UP:
            foj_battle_move_cursor(battle, 0, -1);
            return FOJ_BATTLE_NO_ACTION;
        case FOJ_REPLAY_DOWN:
            foj_battle_move_cursor(battle, 0, 1);
            return FOJ_BATTLE_NO_ACTION;
        case FOJ_REPLAY_LEFT:
            foj_battle_move_cursor(battle, -1, 0);
            return FOJ_BATTLE_NO_ACTION;
        case FOJ_REPLAY_RIGHT:
            foj_battle_move_cursor(battle, 1, 0);
            return FOJ_BATTLE_NO_ACTION;
        case FOJ_REPLAY_A: return foj_battle_confirm(battle);
        case FOJ_REPLAY_B: return foj_battle_cancel(battle);
        case FOJ_REPLAY_X: return foj_battle_attack(battle);
        case FOJ_REPLAY_ZR: return foj_battle_guard(battle);
        case FOJ_REPLAY_Y: return foj_battle_end_turn(battle);
        case FOJ_REPLAY_RESET:
            foj_battle_init(battle);
            return FOJ_BATTLE_NO_ACTION;
        default: return FOJ_BATTLE_REJECTED;
    }
}

bool foj_replay_record(FojBattleReplay *log, FojBattle *battle,
                       FojReplayCommand command, FojBattleEvent *event) {
    if (!log || !battle || (unsigned)command >= FOJ_REPLAY_COMMAND_COUNT ||
        log->count >= FOJ_REPLAY_MAX_INPUTS) {
        if (event) *event = FOJ_BATTLE_REJECTED;
        return false;
    }
    /* Appending only after validation avoids a partial log on failure. */
    FojBattleEvent result = execute_command(battle, command);
    log->commands[log->count++] = (uint8_t)command;
    if (event) *event = result;
    return true;
}

bool foj_replay_reconstruct(const FojBattleReplay *log,
                            FojBattle *reconstructed) {
    if (!log || !reconstructed || log->count > FOJ_REPLAY_MAX_INPUTS)
        return false;
    FojBattle replayed;
    foj_battle_init(&replayed);
    for (uint16_t index = 0; index < log->count; ++index) {
        if (log->commands[index] >= FOJ_REPLAY_COMMAND_COUNT)
            return false;
        (void)execute_command(&replayed,
                              (FojReplayCommand)log->commands[index]);
    }
    *reconstructed = replayed;
    return true;
}

bool foj_replay_matches(const FojBattleReplay *log,
                         const FojBattle *live) {
    if (!live) return false;
    FojBattle reconstructed;
    if (!foj_replay_reconstruct(log, &reconstructed)) return false;
    return memcmp(&reconstructed, live, sizeof(*live)) == 0;
}
