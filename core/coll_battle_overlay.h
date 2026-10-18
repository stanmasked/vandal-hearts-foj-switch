#ifndef FOJ_COLL_BATTLE_OVERLAY_H
#define FOJ_COLL_BATTLE_OVERLAY_H

/* Stage221: raw COLL observation heatmap layered on SYNTHETIC combat.
 * Numeric values/flags have unknown game semantics. All parameters are
 * local-only; this function never changes the tactical battle state. */
#include <stdbool.h>
#include <stdint.h>
#include "coll_battle_window.h"

bool foj_coll_battle_overlay(const FojCollBattleWindow *window,
                              uint32_t *pixels, int width, int height,
                              int stride_pixels, int cursor_x, int cursor_y,
                              unsigned channel);

#endif
