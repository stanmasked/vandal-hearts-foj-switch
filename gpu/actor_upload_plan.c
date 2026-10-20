#include "actor_upload_plan.h"
#include <stdint.h>

_Static_assert(sizeof(FojGpuVertex)==24,
               "Gpu vertex payload layout unexpectedly changed");

FojGpuStreamStatus foj_gpu_actor_upload_plan(
    const FojGpuBatch *batches,size_t batch_count,size_t vertex_count,
    size_t material_count,size_t gpu_alignment,
    FojGpuActorUploadPlan *out) {
    if (!batches || !out)return FOJ_GPU_STREAM_ARGUMENT;
    if (gpu_alignment<16u || gpu_alignment>(size_t)1048576u ||
        (gpu_alignment & (gpu_alignment-1u))!=0u)
        return FOJ_GPU_STREAM_BOUNDS;

    /* Existing draw-plan validator enforces triangle counts, a completely
     * covered contiguous stream, per-section ordering and material bounds.
     * Local scratch prevents partially visible caller writes on failure. */
    FojGpuDrawRange checked[FOJ_GPU_MAX_BATCHES];
    FojGpuStreamStatus status=foj_gpu_build_draw_plan(
        batches,batch_count,vertex_count,material_count,
        checked,FOJ_GPU_MAX_BATCHES);
    if (status!=FOJ_GPU_STREAM_OK)return status;

    const uint64_t payload=(uint64_t)vertex_count*sizeof(FojGpuVertex);
    const uint64_t aligned=(payload+(uint64_t)gpu_alignment-1u) &
                           ~((uint64_t)gpu_alignment-1u);
    if (!payload || aligned>UINT32_MAX ||
        aligned<payload)return FOJ_GPU_STREAM_BOUNDS;

    uint32_t used_mask=0;
    for (size_t i=0;i<batch_count;++i)
        used_mask|=UINT32_C(1)<<checked[i].material_index;

    const FojGpuActorUploadPlan plan={
        (uint32_t)payload,(uint32_t)aligned,
        used_mask,(uint32_t)batch_count
    };
    *out=plan;
    return FOJ_GPU_STREAM_OK;
}
