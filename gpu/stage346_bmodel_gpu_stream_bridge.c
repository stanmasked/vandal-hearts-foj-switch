#include "stage346_bmodel_gpu_stream_bridge.h"

#include <math.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>

static int overlaps(const void *a_ptr, size_t a_size,
                    const void *b_ptr, size_t b_size) {
    uintptr_t a, b;
    if (a_size == 0u || b_size == 0u) return 0;
    if (a_ptr == NULL || b_ptr == NULL) return 1;
    a = (uintptr_t)a_ptr;
    b = (uintptr_t)b_ptr;
    if (a_size > UINTPTR_MAX - a || b_size > UINTPTR_MAX - b) return 1;
    return a < b + b_size && b < a + a_size;
}

static int plan_is_empty(const FojStage346BmodelGpuPlan *plan) {
    if (plan == NULL || plan->stream.vertices_written != 0u ||
        plan->stream.batches_written != 0u ||
        plan->stream.camera_depth_min != 0.0f ||
        plan->stream.camera_depth_max != 0.0f ||
        plan->upload.payload_bytes != 0u ||
        plan->upload.allocation_bytes != 0u ||
        plan->upload.material_mask != 0u ||
        plan->upload.batch_count != 0u ||
        plan->texture_count != 0u || plan->source_data != NULL ||
        plan->source_size != 0u) return 0;
    for (size_t i = 0u; i < FOJ_GPU_MAX_TEXTURES; ++i) {
        if (plan->texture_refs[i].material_index != 0u ||
            plan->texture_refs[i].basename.offset != 0u ||
            plan->texture_refs[i].basename.length != 0u) return 0;
    }
    return 1;
}

static int refs_equal(const uint8_t *data, size_t size,
                      FojStage343StringRef a, FojStage343StringRef b) {
    if (data == NULL || a.offset > size || b.offset > size ||
        a.length > size - a.offset || b.length > size - b.offset ||
        a.length != b.length) return 0;
    return memcmp(data + a.offset, data + b.offset, a.length) == 0;
}

FojGpuStreamStatus foj_gpu_stage346_bmodel_prepare(
    const uint8_t *bmodel_bytes, size_t bmodel_size,
    const FojTextureCamera *camera, unsigned width, unsigned height,
    size_t gpu_alignment, FojGpuVertex *vertices_out, size_t vertex_capacity,
    FojGpuBatch *batches_out, size_t batch_capacity,
    FojStage346BmodelGpuPlan *plan) {
    FojStage345BmodelMesh mesh = {0};
    FojTexturedVertex *source = NULL;
    FojTextureSection sections[FOJ_GPU_MAX_BATCHES];
    FojGpuBatch checked_batches[FOJ_GPU_MAX_BATCHES];
    FojStage346BmodelGpuPlan staged_plan;
    FojGpuActorUploadPlan upload = {0};
    FojGpuStreamInfo stream = {0};
    FojGpuStreamStatus result = FOJ_GPU_STREAM_INVALID;
    if (bmodel_bytes == NULL || camera == NULL || vertices_out == NULL ||
        batches_out == NULL || plan == NULL || !plan_is_empty(plan))
        return FOJ_GPU_STREAM_ARGUMENT;
    if (bmodel_size > FOJ_STAGE343_MAX_MODEL_BYTES)
        return FOJ_GPU_STREAM_BOUNDS;
    if (overlaps(bmodel_bytes, bmodel_size, plan, sizeof(*plan)))
        return FOJ_GPU_STREAM_ARGUMENT;

    FojStage345Status parsed = foj_stage345_bmodel_to_rigmesh(
        bmodel_bytes, bmodel_size, &mesh);
    if (parsed != FOJ_STAGE345_OK ||
        !foj_stage345_mesh_integrity_ready(&mesh)) {
        result = parsed == FOJ_STAGE345_LIMIT || parsed == FOJ_STAGE345_MEMORY
            ? FOJ_GPU_STREAM_BOUNDS : FOJ_GPU_STREAM_INVALID;
        goto done;
    }
    if (mesh.mesh.vertex_count > FOJ_GPU_MAX_VERTICES ||
        mesh.mesh.section_count > FOJ_GPU_MAX_BATCHES ||
        vertex_capacity < mesh.mesh.vertex_count ||
        batch_capacity < mesh.mesh.section_count) {
        result = FOJ_GPU_STREAM_BOUNDS;
        goto done;
    }
    if (mesh.mesh.vertex_count > SIZE_MAX / sizeof(*vertices_out) ||
        mesh.mesh.vertex_count > SIZE_MAX / sizeof(*source) ||
        mesh.mesh.section_count > SIZE_MAX / sizeof(*batches_out)) {
        result = FOJ_GPU_STREAM_BOUNDS;
        goto done;
    }
    const size_t vertex_bytes = mesh.mesh.vertex_count * sizeof(*vertices_out);
    const size_t batch_bytes = mesh.mesh.section_count * sizeof(*batches_out);
    if (overlaps(bmodel_bytes, bmodel_size, vertices_out, vertex_bytes) ||
        overlaps(bmodel_bytes, bmodel_size, batches_out, batch_bytes) ||
        overlaps(vertices_out, vertex_bytes, batches_out, batch_bytes) ||
        overlaps(vertices_out, vertex_bytes, plan, sizeof(*plan)) ||
        overlaps(batches_out, batch_bytes, plan, sizeof(*plan)) ||
        overlaps(camera, sizeof(*camera), vertices_out, vertex_bytes) ||
        overlaps(camera, sizeof(*camera), batches_out, batch_bytes) ||
        overlaps(camera, sizeof(*camera), plan, sizeof(*plan))) {
        result = FOJ_GPU_STREAM_ARGUMENT;
        goto done;
    }

    FojStage343TextureRef unique_textures[FOJ_GPU_MAX_TEXTURES];
    size_t unique_count = 0u;
    for (size_t s = 0u; s < mesh.mesh.section_count; ++s) {
        const uint16_t material_index = mesh.section_material_indices[s];
        if (material_index >= mesh.material_count) {
            result = FOJ_GPU_STREAM_INVALID;
            goto done;
        }
        const FojStage343Material *material = &mesh.materials[material_index];
        if (material->texture_count != 1u ||
            material->first_texture >= mesh.texture_count) {
            result = FOJ_GPU_STREAM_INVALID;
            goto done;
        }
        const FojStage343TextureRef texture =
            mesh.textures[material->first_texture];
        size_t slot = 0u;
        for (; slot < unique_count; ++slot) {
            if (refs_equal(mesh.source_data, mesh.source_size,
                           unique_textures[slot].basename,
                           texture.basename)) break;
        }
        if (slot == unique_count) {
            if (unique_count >= FOJ_GPU_MAX_TEXTURES) {
                result = FOJ_GPU_STREAM_BOUNDS;
                goto done;
            }
            unique_textures[unique_count++] = texture;
        }
        sections[s] = (FojTextureSection){
            mesh.mesh.sections[s].start_vertex,
            mesh.mesh.sections[s].vertex_count,
            (unsigned)slot
        };
        checked_batches[s] = (FojGpuBatch){
            mesh.mesh.sections[s].start_vertex,
            mesh.mesh.sections[s].vertex_count,
            (uint32_t)slot
        };
    }
    if (unique_count == 0u) {
        result = FOJ_GPU_STREAM_INVALID;
        goto done;
    }

    result = foj_gpu_actor_upload_plan(
        checked_batches, mesh.mesh.section_count, mesh.mesh.vertex_count,
        unique_count, gpu_alignment, &upload);
    if (result != FOJ_GPU_STREAM_OK) goto done;
    const uint32_t expected_mask =
        (UINT32_C(1) << (unsigned)unique_count) - UINT32_C(1);
    if (upload.material_mask != expected_mask) {
        result = FOJ_GPU_STREAM_INVALID;
        goto done;
    }

    source = malloc(mesh.mesh.vertex_count * sizeof(*source));
    if (source == NULL) {
        result = FOJ_GPU_STREAM_BOUNDS;
        goto done;
    }
    for (size_t i = 0u; i < mesh.mesh.vertex_count; ++i) {
        source[i] = (FojTexturedVertex){
            mesh.mesh.vertices[i].xyz[0],
            mesh.mesh.vertices[i].xyz[1],
            mesh.mesh.vertices[i].xyz[2],
            mesh.mesh.attributes[i].uv[0],
            mesh.mesh.attributes[i].uv[1]
        };
        if (!isfinite(source[i].x) || !isfinite(source[i].y) ||
            !isfinite(source[i].z) || !isfinite(source[i].u) ||
            !isfinite(source[i].v)) {
            result = FOJ_GPU_STREAM_INVALID;
            goto done;
        }
    }

    /* This is deliberately the final fallible operation before committing
     * plan metadata: foj_gpu_prepare_stream validates every input before it
     * writes either output array. No GPU command is submitted in this stage.
     */
    result = foj_gpu_prepare_stream(
        source, mesh.mesh.vertex_count, sections, mesh.mesh.section_count,
        unique_count, camera, width, height, vertices_out, vertex_capacity,
        batches_out, batch_capacity, &stream);
    if (result != FOJ_GPU_STREAM_OK) goto done;

    memset(&staged_plan, 0, sizeof(staged_plan));
    staged_plan.stream = stream;
    staged_plan.upload = upload;
    staged_plan.texture_count = unique_count;
    memcpy(staged_plan.texture_refs, unique_textures,
           unique_count * sizeof(unique_textures[0]));
    staged_plan.source_data = mesh.source_data;
    staged_plan.source_size = mesh.source_size;
    *plan = staged_plan;

done:
    free(source);
    foj_stage345_bmodel_mesh_free(&mesh);
    return result;
}
