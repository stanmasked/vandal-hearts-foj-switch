#ifndef FOJ_GPU_PRIVATE_ACTOR_BRIDGE_H
#define FOJ_GPU_PRIVATE_ACTOR_BRIDGE_H
/*
 * Stage257: opt-in user-owned FOJRM001 + FOJMAT01 to GPU vertex stream.
 *
 * These are research interchange containers, NOT native PS3 encodings.
 * This module consumes caller-provided private bytes and emits no source
 * files, telemetry, shader code, or game content into the repository.
 * It prepares static/bind-pose XYZ + UV only; no original animation or GPU
 * draw/presentation is performed.
 */
#include <stddef.h>
#include <stdint.h>
#include "gpu_vertex_stream.h"
#include "actor_upload_plan.h"

typedef struct {
    FojGpuStreamInfo stream;
    FojGpuActorUploadPlan upload;
} FojGpuPrivateActorPlan;

/*
 * All output buffers and *plan remain unchanged on any error.
 * Caller owns the uploaded original-data buffers, and frees/releases them.
 * Input data is validated via existing FOJRM001/FOJMAT01 parsers and the
 * Stage256 batch-allocation validator before conversion.
 * Alignment is a power-of-two in [16, 1048576], normally 4096 on Switch.
 * On success the caller receives ordered FojGpuVertex and FojGpuBatch
 * output suitable for a later *separately validated* GPU upload.
 */
FojGpuStreamStatus foj_gpu_private_actor_prepare(
    const uint8_t *mesh_bytes, size_t mesh_len,
    const uint8_t *material_bytes, size_t material_len,
    const FojTextureCamera *camera, unsigned framebuffer_width,
    unsigned framebuffer_height, size_t gpu_alignment,
    FojGpuVertex *vertices_out, size_t vertex_capacity,
    FojGpuBatch *batches_out, size_t batch_capacity,
    FojGpuPrivateActorPlan *plan);

#endif
