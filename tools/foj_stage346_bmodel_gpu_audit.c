#include "../gpu/stage346_bmodel_gpu_stream_bridge.h"

#include <stdio.h>
#include <stdlib.h>

static int run_audit(const char *path) {
    FILE *file = fopen(path, "rb");
    uint8_t *bytes = NULL;
    long length;
    FojGpuVertex *vertices = NULL;
    FojGpuBatch *batches = NULL;
    FojStage346BmodelGpuPlan plan = {0};
    int result = 2;
    if (file == NULL) {
        puts("{\"ok\":false,\"reason\":\"input_open\"}");
        return 2;
    }
    if (fseek(file, 0L, SEEK_END) != 0 || (length = ftell(file)) <= 0L ||
        (unsigned long)length > FOJ_STAGE343_MAX_MODEL_BYTES ||
        fseek(file, 0L, SEEK_SET) != 0) {
        fclose(file);
        puts("{\"ok\":false,\"reason\":\"input_size\"}");
        return 2;
    }
    bytes = (uint8_t *)malloc((size_t)length);
    if (bytes == NULL) {
        fclose(file);
        puts("{\"ok\":false,\"reason\":\"allocation\"}");
        return 2;
    }
    if (fread(bytes, 1u, (size_t)length, file) != (size_t)length ||
        fclose(file) != 0) {
        free(bytes);
        puts("{\"ok\":false,\"reason\":\"input_read\"}");
        return 2;
    }
    FojStage345BmodelMesh parsed = {0};
    FojStage345Status ps = foj_stage345_bmodel_to_rigmesh(bytes, (size_t)length, &parsed);
    if (ps != FOJ_STAGE345_OK) {
        printf("{\"ok\":false,\"parse_status\":%u}\n", (unsigned)ps);
        foj_stage345_bmodel_mesh_free(&parsed);
        free(bytes);
        return 1;
    }
    const size_t vertex_count = parsed.mesh.vertex_count;
    const size_t batch_count = parsed.mesh.section_count;
    foj_stage345_bmodel_mesh_free(&parsed);
    vertices = (FojGpuVertex *)calloc(vertex_count, sizeof(*vertices));
    batches = (FojGpuBatch *)calloc(batch_count, sizeof(*batches));
    if (vertices == NULL || batches == NULL) {
        free(vertices); free(batches); free(bytes);
        puts("{\"ok\":false,\"reason\":\"allocation\"}");
        return 2;
    }
    const FojTextureCamera camera = {0.0f,0.0f,0.0f,9.5f,0.0f,0.0f,1.0f,0};
    FojGpuStreamStatus status = foj_gpu_stage346_bmodel_prepare(
        bytes, (size_t)length, &camera, 1280u, 720u, 256u,
        vertices, vertex_count, batches, batch_count, &plan);
    if (status != FOJ_GPU_STREAM_OK) {
        printf("{\"ok\":false,\"gpu_plan_status\":%u}\n", (unsigned)status);
        free(vertices); free(batches); free(bytes);
        return 1;
    }
    printf("{\"ok\":true,\"integrity_ready\":true,"
           "\"sections\":%zu,\"gpu_vertices\":%zu,\"gpu_batches\":%zu,"
           "\"texture_slots\":%zu,\"payload_bytes\":%u,"
           "\"allocation_bytes\":%u,\"material_mask\":%u,"
           "\"depth_min\":%.6f,\"depth_max\":%.6f}\n",
           plan.stream.batches_written, plan.stream.vertices_written,
           plan.stream.batches_written, plan.texture_count,
           plan.upload.payload_bytes, plan.upload.allocation_bytes,
           plan.upload.material_mask, plan.stream.camera_depth_min,
           plan.stream.camera_depth_max);
    result = 0;
    free(vertices); free(batches); free(bytes);
    return result;
}

int main(int argc, char **argv) {
    if (argc != 2) {
        puts("{\"ok\":false,\"reason\":\"one_input_path_required\"}");
        return 64;
    }
    return run_audit(argv[1]);
}
