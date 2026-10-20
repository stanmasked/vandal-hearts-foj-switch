#ifndef FOJ_GPU_THREE_LAYER_PREFLIGHT_H
#define FOJ_GPU_THREE_LAYER_PREFLIGHT_H
/* Stage270: conservative native research geometry preflight.
 * Coordinates are Stage267 orthographic GPU clip XYZ (constant w=1).
 * Fixed material order is 0 nearest, 1 middle, 2 opaque rear.
 * Does NOT support perspective, polygon intersections, or general OIT.
 * This pure C11 module has no Nintendo SDK, file system or game assets. */
#include <stddef.h>
#include "gpu_vertex_stream.h"

typedef enum {
    FOJ_THREE_ORDER_OK = 0,
    FOJ_THREE_ORDER_INVALID = 1,
    FOJ_THREE_ORDER_UNSAFE = 2
} FojThreeOrderStatus;

/* Returns OK only when every overlapping projected triangle pair has the
 * same strict front-to-back relationship as fixed draw order [2,1,0].
 * On invalid data or ambiguity, do NOT submit any GPU scene commands. */
FojThreeOrderStatus foj_three_layer_preflight(
    const FojGpuVertex *vertices, size_t vertex_count,
    const FojGpuBatch *batches, size_t batch_count);
#endif
