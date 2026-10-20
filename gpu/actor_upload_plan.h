#ifndef FOJ_GPU_ACTOR_UPLOAD_PLAN_H
#define FOJ_GPU_ACTOR_UPLOAD_PLAN_H

/* Research-only GPU vertex reservation for up to 64 ordered batches.
 * No proprietary model bytes or Switch GPU commands live here.
 * This can validate private FOJRM/FOJMAT section layouts after they have
 * been independently converted to an FojGpuBatch array. */
#include "gpu_draw_plan.h"
#include <stddef.h>
#include <stdint.h>

typedef struct {
    uint32_t payload_bytes;       /* exact vertex-stream byte count */
    uint32_t allocation_bytes;    /* rounded for GPU memory block */
    uint32_t material_mask;       /* bit i: material i is referenced */
    uint32_t batch_count;
} FojGpuActorUploadPlan;

/* Validate all batches before touching output; reserve vertices once for
 * the whole ordered multi-material draw sequence. Power-of-two alignment
 * must be between 16 and 1 MiB; actual GPU memory still needs a device.
 * Returns the usual FojGpuStreamStatus codes. On ANY error *out is untouched.
 * Batch input and output must not alias. */
FojGpuStreamStatus foj_gpu_actor_upload_plan(
    const FojGpuBatch *batches, size_t batch_count, size_t vertex_count,
    size_t material_count, size_t gpu_alignment,
    FojGpuActorUploadPlan *out);

#endif
