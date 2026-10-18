#ifndef FOJ_BATTLE_REPLAY_METER_H
#define FOJ_BATTLE_REPLAY_METER_H

/* Generated-only software HUD meter for deterministic replay history. */
#include "battle_replay.h"
#include <stdbool.h>
#include <stdint.h>

enum {
    FOJ_REPLAY_METER_X = 28,
    FOJ_REPLAY_METER_Y = 12,
    FOJ_REPLAY_METER_HEIGHT = 8,
    FOJ_REPLAY_METER_MIN_WIDTH = 156,
    FOJ_REPLAY_METER_MIN_HEIGHT = 20
};

bool foj_replay_render_meter(const FojBattleReplay *log,
                             uint32_t *pixels, int width, int height,
                             int stride);

#endif
