#ifndef FOJ_GPU_DRAW_PLAN_H
#define FOJ_GPU_DRAW_PLAN_H
/* Validate consecutive triangle-soup batches before any GPU draw calls.
 * texture_index is metadata only: this layer does NOT bind materials. */
#include "gpu_vertex_stream.h"
typedef struct {
    uint32_t first_vertex,vertex_count,material_index;
} FojGpuDrawRange;

/* Transactional: failures never modify draws_out. */
FojGpuStreamStatus foj_gpu_build_draw_plan(
    const FojGpuBatch *batches,size_t batch_count,
    size_t vertex_count,size_t material_count,
    FojGpuDrawRange *draws_out,size_t draw_capacity);
#endif
