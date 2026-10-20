#ifndef FOJ_GPU_ALPHA_MATERIAL_CONTRACT_H
#define FOJ_GPU_ALPHA_MATERIAL_CONTRACT_H
/* Stage273 SDK-free guard for the one mandatory opaque rear atlas.
 * The dynamic draw planner puts this atlas first with blending disabled and
 * depth writing enabled; it must not contain transparent texels.
 * All data is already decoded and retained by the private bundle intake.
 * No material contents are logged or copied.
 */
#include <stdint.h>
#include "atlas_dds.h"
int foj_gpu_opaque_rear_atlas(
    const uint8_t *pixels, const FojAtlasRgba8Info *info);
#endif
