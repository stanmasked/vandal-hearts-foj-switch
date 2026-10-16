#ifndef FOJ_SMOKE_PLAN_H
#define FOJ_SMOKE_PLAN_H
#include <stdint.h>

/* Platform-neutral math used by the shaderless Switch GPU smoke test.
 * Does not link deko3d; resource lifetimes remain on the Switch. */
int foj_smoke_image_allocation(uint64_t image_size,
                               uint32_t image_alignment,
                               uint32_t memory_alignment,
                               uint32_t *result_bytes);
int foj_smoke_color(unsigned color_index, float result_rgba[4]);
unsigned foj_smoke_color_for_frame(uint64_t frame);
#endif
