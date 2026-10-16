#ifndef FOJ_ISOMETRIC_DEMO_H
#define FOJ_ISOMETRIC_DEMO_H

/* Portable CPU rasterizer for generated isometric height-map research.
 * Not a PS3 renderer, 3D-model loader, or original FoJ asset decoder. */
#include <stdint.h>
#include "tactical_demo.h"

void foj_iso_project(int width, int height, int x, int y, int elevation,
                     int *screen_x, int *screen_y);
void foj_iso_render(const FojDemo *state, uint32_t *pixels,
                    int width, int height, int stride_pixels);

#endif
