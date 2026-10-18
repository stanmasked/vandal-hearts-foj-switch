#ifndef FOJ_COLL_ISO_VIEW_H
#define FOJ_COLL_ISO_VIEW_H

#include "coll_grid.h"
#include <stdint.h>

/* Diagnostic isometric DATA plot for 6 raw COLL columns.
 * Numeric columns 0..3 are normalized into a VISUAL extrusion 0..32 px.
 * The extrusion is not a claim about physical ground elevation.
 * Boolean columns 4..5 use flat colored diamonds, not collision logic.
 * This module does not implement FoJ tactics or alter COLL resources.
 * Invalid inputs must leave framebuffer bytes untouched. */
void foj_coll_iso_render(const FojCollGrid *grid, uint32_t *pixels,
                         int width, int height, int stride,
                         int cursor_x, int cursor_y,
                         int tile_size, int channel);

#endif
