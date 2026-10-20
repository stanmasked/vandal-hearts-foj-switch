#ifndef FOJ_GPU_TRANSPARENT_ORDER_GUARD_H
#define FOJ_GPU_TRANSPARENT_ORDER_GUARD_H
/* Stage269: fail-closed native preflight for the generated three-triangle
 * orthographic research mode only. No original PS3 resource handling.
 * Return OK only if fixed pass order rear(2), middle(1), front(0)
 * is mathematically valid over every overlapping screen-space region.
 */
#include <stddef.h>
#include "gpu_vertex_stream.h"

typedef enum {
    FOJ_GPU_ORDER_OK=0,
    FOJ_GPU_ORDER_ARGUMENT,
    FOJ_GPU_ORDER_UNSUPPORTED,
    FOJ_GPU_ORDER_UNSAFE
} FojGpuOrderStatus;

FojGpuOrderStatus foj_gpu_three_layer_order_guard(
    const FojGpuVertex *vertices, size_t vertex_count,
    const FojGpuBatch *batches, size_t batch_count);

const char *foj_gpu_order_status_name(FojGpuOrderStatus status);

#endif
