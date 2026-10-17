#include "gpu_draw_plan.h"
#include <stdint.h>

FojGpuStreamStatus foj_gpu_build_draw_plan(
    const FojGpuBatch *batches,size_t batch_count,
    size_t vertex_count,size_t material_count,
    FojGpuDrawRange *draws_out,size_t draw_capacity) {
    if (!batches||!draws_out)return FOJ_GPU_STREAM_ARGUMENT;
    if (!batch_count||batch_count>FOJ_GPU_MAX_BATCHES||
        !vertex_count||vertex_count%3||vertex_count>FOJ_GPU_MAX_VERTICES||
        !material_count||material_count>FOJ_GPU_MAX_TEXTURES||
        draw_capacity<batch_count)
        return FOJ_GPU_STREAM_BOUNDS;
    /* Two passes preserve the caller's output when any later batch fails. */
    uint64_t covered=0;
    for (size_t i=0;i<batch_count;++i) {
        const FojGpuBatch *b=&batches[i];
        if (b->first_vertex!=covered||!b->vertex_count||
            b->vertex_count%3||b->vertex_count>vertex_count-covered||
            b->texture_index>=material_count)
            return FOJ_GPU_STREAM_INVALID;
        covered+=b->vertex_count;
    }
    if (covered!=vertex_count)return FOJ_GPU_STREAM_INVALID;
    for (size_t i=0;i<batch_count;++i) {
        draws_out[i]=(FojGpuDrawRange){
            batches[i].first_vertex,
            batches[i].vertex_count,
            batches[i].texture_index
        };
    }
    return FOJ_GPU_STREAM_OK;
}
