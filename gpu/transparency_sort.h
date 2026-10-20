#ifndef FOJ_GPU_TRANSPARENCY_SORT_H
#define FOJ_GPU_TRANSPARENCY_SORT_H

/* Stage272: portable geometry-only back-to-front research order.
 * This is NOT a deko3d submission API. The caller must actually honor the
 * result in a future GPU integration, and must separately validate material
 * indices, draw batches, alpha channels and all original input content.
 *
 * Input: 1..64 triangles in contiguous groups of three canonical clip
 * vertices (x,y in [-1,1], z in [0,1], w exactly 1, larger z is nearer).
 * Only orthographic / affine depth is supported (constant homogeneous W).
 * Input and output must not alias. output_capacity >= triangle_count.
 *
 * On failure, *output is unchanged; in particular crossing, coplanar,
 * numerically unstable and cyclic ordering are rejected.
 */
#include <stddef.h>
#include <stdint.h>
#include "gpu_vertex_stream.h"

enum { FOJ_ALPHA_SORT_MAX_TRIANGLES = 64 };

typedef enum {
    FOJ_ALPHA_SORT_OK = 0,
    FOJ_ALPHA_SORT_INVALID = 1,
    FOJ_ALPHA_SORT_UNSAFE = 2
} FojAlphaSortStatus;

FojAlphaSortStatus foj_alpha_sort_back_to_front(
    const FojGpuVertex *vertices,
    size_t triangle_count,
    uint32_t *output,
    size_t output_capacity);

#endif
