#ifndef FOJ_COLL_VIEW_H
#define FOJ_COLL_VIEW_H

#include "coll_grid.h"
#include <stdint.h>

/* Top-down diagnostic heatmap, NOT a recreation of the FoJ PS3 3D engine.
 * channel: 0..3 numeric sample columns, 4 or 5 boolean flag columns.
 * The requested grid is centered if it fits, otherwise cursor-followed.
 */
void foj_coll_render(const FojCollGrid *grid, uint32_t *pixels, int width,
                     int height, int stride, int cursor_x, int cursor_y,
                     int tile_size, int channel);

#endif
