#ifndef FOJ_STAGE346_BMODEL_GPU_STREAM_BRIDGE_H
#define FOJ_STAGE346_BMODEL_GPU_STREAM_BRIDGE_H

#include "stage345_bmodel_mesh_bridge.h"
#include "gpu_vertex_stream.h"
#include "actor_upload_plan.h"

#include <stddef.h>
#include <stdint.h>

/* GPU-ready CPU projection plan for a source BMODEL in bind pose. Texture
 * references point into the borrowed source_data; the caller must keep the
 * original BMODEL bytes alive and unchanged until the plan is discarded.
 * This stage does not decode/load DDS pixels, submit GPU commands, animate
 * bones, or claim the original engine's camera/transform conventions.
 */
typedef struct {
    FojGpuStreamInfo stream;
    FojGpuActorUploadPlan upload;
    FojStage343TextureRef texture_refs[FOJ_GPU_MAX_TEXTURES];
    size_t texture_count;
    const uint8_t *source_data;
    size_t source_size;
} FojStage346BmodelGpuPlan;

/* Fit a diagnostic orthographic camera to the source mesh's bind-pose
 * bounds. This is a debug/inspection camera, not a reconstruction of the
 * original game's camera. Uses a conservative 0.88 clip-space half-extent.
 * The output is unchanged on failure.
 */
FojGpuStreamStatus foj_gpu_stage346_fit_camera(
    const uint8_t *bmodel_bytes, size_t bmodel_size,
    unsigned framebuffer_width, unsigned framebuffer_height,
    FojTextureCamera *camera_out);

/* Requires exactly one texture reference per used material and no more than
 * eight unique texture basenames. All output arrays and plan remain unchanged
 * on failure. The plan must be zero-initialized before first use.
 */
FojGpuStreamStatus foj_gpu_stage346_bmodel_prepare(
    const uint8_t *bmodel_bytes, size_t bmodel_size,
    const FojTextureCamera *camera, unsigned framebuffer_width,
    unsigned framebuffer_height, size_t gpu_alignment,
    FojGpuVertex *vertices_out, size_t vertex_capacity,
    FojGpuBatch *batches_out, size_t batch_capacity,
    FojStage346BmodelGpuPlan *plan);

#endif
