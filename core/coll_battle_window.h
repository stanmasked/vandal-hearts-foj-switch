#ifndef FOJ_COLL_BATTLE_WINDOW_H
#define FOJ_COLL_BATTLE_WINDOW_H

/* Stage218: preserve raw 8x6 COLL records for local research ONLY.
 * This does not establish original walkability, terrain height, combat
 * ranges, or even the in-game interpretation of the four float samples. */
#include <stdbool.h>
#include <stdint.h>

#include "coll_grid.h"
#include "tactical_demo.h"

typedef struct {
    int source_x;
    int source_y;
    int source_width;
    int source_height;
    float raw[FOJ_HEIGHT][FOJ_WIDTH][4];
    uint8_t flags[FOJ_HEIGHT][FOJ_WIDTH][2];
} FojCollBattleWindow;

/* Only accepts a fully parsed grid with enough cells for the complete
 * 8x6 window. Failed requests zero the output, never partially publish it. */
bool foj_coll_battle_window(const FojCollGrid *source, int left, int top,
                             FojCollBattleWindow *window);

/* Index is 0..3 for the unclassified numeric channels. All samples
 * remain unchanged; no elevation quantization or gameplay rules applied. */
bool foj_coll_window_sample(const FojCollBattleWindow *window,
                             int x, int y, unsigned channel,
                             float *value);

bool foj_coll_window_flag(const FojCollBattleWindow *window,
                           int x, int y, unsigned channel,
                           uint8_t *value);

#endif
