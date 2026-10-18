#include "coll_battle_window.h"

#include <math.h>
#include <string.h>

bool foj_coll_battle_window(const FojCollGrid *source, int left, int top,
                            FojCollBattleWindow *window) {
    if (!window) return false;
    memset(window, 0, sizeof(*window));
    if (!source || source->width < FOJ_WIDTH ||
        source->height < FOJ_HEIGHT ||
        source->width > FOJ_COLL_MAX_SIDE ||
        source->height > FOJ_COLL_MAX_SIDE ||
        left < 0 || top < 0 ||
        left > source->width - FOJ_WIDTH ||
        top > source->height - FOJ_HEIGHT) return false;

    /* Reject malformed scalar data or flags before publishing output. */
    for (int y = 0; y < FOJ_HEIGHT; ++y)
        for (int x = 0; x < FOJ_WIDTH; ++x) {
            for (unsigned n = 0; n < 4; ++n)
                if (!isfinite(source->samples[top+y][left+x][n]))
                    return false;
            for (unsigned n = 0; n < 2; ++n)
                if (source->flags[top+y][left+x][n] > 1)
                    return false;
        }

    window->source_x = left;
    window->source_y = top;
    window->source_width = source->width;
    window->source_height = source->height;
    for (int y = 0; y < FOJ_HEIGHT; ++y)
        for (int x = 0; x < FOJ_WIDTH; ++x) {
            for (unsigned n = 0; n < 4; ++n)
                window->raw[y][x][n] = source->samples[top+y][left+x][n];
            for (unsigned n = 0; n < 2; ++n)
                window->flags[y][x][n] = source->flags[top+y][left+x][n];
        }
    return true;
}

bool foj_coll_window_sample(const FojCollBattleWindow *window, int x, int y,
                             unsigned channel, float *value) {
    if (!window || !value || !foj_in_bounds(x, y) || channel >= 4 ||
        window->source_width < FOJ_WIDTH ||
        window->source_height < FOJ_HEIGHT) return false;
    *value = window->raw[y][x][channel];
    return true;
}

bool foj_coll_window_flag(const FojCollBattleWindow *window, int x, int y,
                           unsigned channel, uint8_t *value) {
    if (!window || !value || !foj_in_bounds(x, y) || channel >= 2 ||
        window->source_width < FOJ_WIDTH ||
        window->source_height < FOJ_HEIGHT) return false;
    *value = window->flags[y][x][channel];
    return true;
}
