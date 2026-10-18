#include "battle_replay_meter.h"

#include <stddef.h>

/* Distinct from hero, enemy, guard, warning, win and replay-audit
 * colors so an actual guest screenshot can count controller events. */
enum { FILLED_RGBA = 0xffe5a139u, EMPTY_RGBA = 0xff393129u };

bool foj_replay_render_meter(const FojBattleReplay *log,
                             uint32_t *pixels, int width, int height,
                             int stride) {
    if (!log || !pixels || log->count > FOJ_REPLAY_MAX_INPUTS ||
        width < FOJ_REPLAY_METER_MIN_WIDTH ||
        height < FOJ_REPLAY_METER_MIN_HEIGHT || stride < width)
        return false;
    for (int y=FOJ_REPLAY_METER_Y;
         y<FOJ_REPLAY_METER_Y+FOJ_REPLAY_METER_HEIGHT;++y) {
        uint32_t *row=pixels+(size_t)y*(size_t)stride;
        for (int i=0;i<FOJ_REPLAY_MAX_INPUTS;++i)
            row[FOJ_REPLAY_METER_X+i] = i<log->count ?
                (uint32_t)FILLED_RGBA : (uint32_t)EMPTY_RGBA;
    }
    return true;
}
