#include "stage346_bmodel_gpu_stream_bridge.h"

#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

typedef struct {
    uint8_t *data;
    size_t capacity;
    size_t size;
} Writer;

static void put8(Writer *w, uint8_t v) {
    assert(w->size < w->capacity);
    w->data[w->size++] = v;
}

static void put16(Writer *w, uint16_t v) {
    put8(w, (uint8_t)(v >> 8));
    put8(w, (uint8_t)v);
}

static void put32(Writer *w, uint32_t v) {
    put8(w, (uint8_t)(v >> 24));
    put8(w, (uint8_t)(v >> 16));
    put8(w, (uint8_t)(v >> 8));
    put8(w, (uint8_t)v);
}

static void put_float(Writer *w, float v) {
    uint32_t bits;
    memcpy(&bits, &v, sizeof(bits));
    put32(w, bits);
}

static void put_string8(Writer *w, const char *s) {
    size_t n = strlen(s);
    assert(n > 0u && n <= 255u);
    put8(w, (uint8_t)n);
    for (size_t i = 0u; i < n; ++i) put8(w, (uint8_t)s[i]);
}

static void put_string16(Writer *w, const char *s) {
    size_t n = strlen(s);
    assert(n > 0u && n <= 255u);
    put16(w, (uint16_t)n);
    for (size_t i = 0u; i < n; ++i) put8(w, (uint8_t)s[i]);
}

static void put_shape(Writer *w, const char *name, const char *material,
                      int separator, int skinned, float x_offset) {
    static const float positions[9] = {
        0.0f, 0.0f, 0.0f, 1.0f, 0.0f, 0.0f, 0.0f, 1.0f, 0.0f
    };
    static const float uvs[6] = {0.0f, 0.0f, 1.0f, 0.0f, 0.0f, 1.0f};
    static const float normals[9] = {
        0.0f, 0.0f, 1.0f, 0.0f, 0.0f, 1.0f, 0.0f, 0.0f, 1.0f
    };
    if (separator) put8(w, 0x07u);
    put8(w, 0x01u); put8(w, 0x20u); put8(w, 0x00u);
    put_string8(w, name);
    put8(w, 0x02u); put16(w, 3u);
    for (size_t i = 0u; i < 9u; ++i)
        put_float(w, positions[i] + (i % 3u == 0u ? x_offset : 0.0f));
    put8(w, 0x05u); put16(w, 3u); put8(w, 0x00u); put8(w, 0x03u);
    for (size_t i = 0u; i < 6u; ++i) put_float(w, uvs[i]);
    put8(w, 0x10u); put16(w, 3u);
    for (size_t i = 0u; i < 9u; ++i) put_float(w, normals[i]);
    put8(w, 0x15u); put16(w, 1u);
    put_float(w, 0.0f); put_float(w, 0.0f); put_float(w, -1.0f);
    put8(w, 0x04u); put16(w, 3u);
    put16(w, 0u); put16(w, 1u); put16(w, 2u);
    if (skinned) {
        put8(w, 0x0fu); put16(w, 6u); put16(w, 2u);
        for (size_t v = 0u; v < 3u; ++v) {
            put16(w, 0u); put_float(w, 0.25f);
            put16(w, 1u); put_float(w, 0.75f);
        }
    }
    put8(w, 0x14u); put_string16(w, material);
    put8(w, 0x21u);
    put_float(w, x_offset); put_float(w, 0.0f); put_float(w, 0.0f);
    put_float(w, x_offset + 1.0f); put_float(w, 1.0f); put_float(w, 0.0f);
}

static void put_rig(Writer *w) {
    put8(w, 0x0au); put16(w, 2u);
    for (uint16_t i = 0u; i < 2u; ++i) {
        put16(w, i == 0u ? UINT16_MAX : 0u); put16(w, 0u);
        put_float(w, 0.0f); put_float(w, 0.0f);
        put_float(w, 0.0f); put_float(w, 1.0f);
        put_float(w, 0.0f); put_float(w, i == 0u ? 0.0f : 2.0f);
        put_float(w, 0.0f);
    }
    put8(w, 0x0cu);
}

static size_t make_fixture(uint8_t *data, size_t capacity,
                           int same_material, int multi_texture) {
    Writer w = {data, capacity, 0u};
    put8(&w, 0x0bu); put8(&w, 0x09u); put8(&w, 0x00u); put8(&w, 2u);
    put_shape(&w, "meshA", "matA", 0, 1, 0.0f);
    put_shape(&w, "meshB", same_material ? "matA" : "matB", 1, 0, 2.0f);
    put8(&w, 0x07u);
    put8(&w, 0x06u); put_string16(&w, "matA");
    put16(&w, (uint16_t)(multi_texture ? 2u : 1u));
    put_string16(&w, "texA.tga");
    if (multi_texture) put_string16(&w, "texA_extra.tga");
    put8(&w, 0x06u); put_string16(&w, "matB"); put16(&w, 1u);
    put_string16(&w, same_texture ? "texA.tga" : "texB.tga");
    put_rig(&w);
    return w.size;
}

static const FojTextureCamera kCamera = {
    0.0f, 0.0f, 0.0f, 9.5f, 0.0f, 0.0f, 1.0f, 0
};

static void test_two_sections_create_ordered_gpu_batches(void) {
    uint8_t data[4096];
    FojGpuVertex vertices[6];
    FojGpuBatch batches[2];
    FojStage346BmodelGpuPlan plan;
    size_t size = make_fixture(data, sizeof(data), 0, 0);
    memset(vertices, 0xa5, sizeof(vertices));
    memset(batches, 0x5a, sizeof(batches));
    memset(&plan, 0, sizeof(plan));
    assert(foj_gpu_stage346_bmodel_prepare(data, size, &kCamera, 1280u, 720u,
           256u, vertices, 6u, batches, 2u, &plan) == FOJ_GPU_STREAM_OK);
    assert(plan.stream.vertices_written == 6u);
    assert(plan.stream.batches_written == 2u);
    assert(plan.upload.payload_bytes == 144u);
    assert(plan.upload.allocation_bytes == 256u);
    assert(plan.upload.material_mask == 3u && plan.upload.batch_count == 2u);
    assert(plan.texture_count == 2u && plan.source_data == data);
    assert(plan.source_size == size);
    assert(batches[0].first_vertex == 0u && batches[0].vertex_count == 3u);
    assert(batches[0].texture_index == 0u);
    assert(batches[1].first_vertex == 3u && batches[1].vertex_count == 3u);
    assert(batches[1].texture_index == 1u);
    assert(vertices[0].u == 0.0f && vertices[1].u == 1.0f);
    assert(vertices[2].v == 1.0f);
    assert(foj_stage343_string_equals(data, size,
           plan.texture_refs[0].basename, "texA.tga"));
    assert(foj_stage343_string_equals(data, size,
           plan.texture_refs[1].basename, "texB.tga"));
}

static void test_sections_sharing_one_material_share_one_slot(void) {
    uint8_t data[4096];
    FojGpuVertex vertices[6];
    FojGpuBatch batches[2];
    FojStage346BmodelGpuPlan plan = {0};
    size_t size = make_fixture(data, sizeof(data), 1, 0);
    assert(foj_gpu_stage346_bmodel_prepare(data, size, &kCamera, 1280u, 720u,
           256u, vertices, 6u, batches, 2u, &plan) == FOJ_GPU_STREAM_OK);
    assert(plan.texture_count == 1u);
    assert(plan.upload.material_mask == 1u);
    assert(batches[0].texture_index == 0u && batches[1].texture_index == 0u);
}

static void test_multi_texture_material_is_refused_transactionally(void) {
    uint8_t data[4096];
    FojGpuVertex vertices[6], before_vertices[6];
    FojGpuBatch batches[2], before_batches[2];
    FojStage346BmodelGpuPlan plan = {0}, before_plan = {0};
    size_t size = make_fixture(data, sizeof(data), 0, 1);
    memset(vertices, 0xa5, sizeof(vertices));
    memset(batches, 0x5a, sizeof(batches));
    memcpy(before_vertices, vertices, sizeof(vertices));
    memcpy(before_batches, batches, sizeof(batches));
    assert(foj_gpu_stage346_bmodel_prepare(data, size, &kCamera, 1280u, 720u,
           256u, vertices, 6u, batches, 2u, &plan) == FOJ_GPU_STREAM_INVALID);
    assert(memcmp(vertices, before_vertices, sizeof(vertices)) == 0);
    assert(memcmp(batches, before_batches, sizeof(batches)) == 0);
    assert(memcmp(&plan, &before_plan, sizeof(plan)) == 0);
}

static void test_capacity_and_camera_failures_leave_outputs_unchanged(void) {
    uint8_t data[4096];
    FojGpuVertex vertices[6], before_vertices[6];
    FojGpuBatch batches[2], before_batches[2];
    FojStage346BmodelGpuPlan plan = {0}, before_plan = {0};
    size_t size = make_fixture(data, sizeof(data), 0, 0);
    memset(vertices, 0x31, sizeof(vertices));
    memset(batches, 0x72, sizeof(batches));
    memcpy(before_vertices, vertices, sizeof(vertices));
    memcpy(before_batches, batches, sizeof(batches));
    assert(foj_gpu_stage346_bmodel_prepare(data, size, &kCamera, 1280u, 720u,
           256u, vertices, 5u, batches, 2u, &plan) == FOJ_GPU_STREAM_BOUNDS);
    assert(memcmp(vertices, before_vertices, sizeof(vertices)) == 0);
    assert(memcmp(batches, before_batches, sizeof(batches)) == 0);
    assert(memcmp(&plan, &before_plan, sizeof(plan)) == 0);

    FojTextureCamera bad_camera = kCamera;
    bad_camera.extent = 0.0f;
    assert(foj_gpu_stage346_bmodel_prepare(data, size, &bad_camera, 1280u, 720u,
           256u, vertices, 6u, batches, 2u, &plan) == FOJ_GPU_STREAM_INVALID);
    assert(memcmp(vertices, before_vertices, sizeof(vertices)) == 0);
    assert(memcmp(batches, before_batches, sizeof(batches)) == 0);
    assert(memcmp(&plan, &before_plan, sizeof(plan)) == 0);
}

static void test_camera_aliasing_output_is_rejected_transactionally(void) {
    uint8_t data[4096];
    union {
        FojGpuVertex vertices[6];
        FojTextureCamera camera;
    } shared;
    FojGpuBatch batches[2], before_batches[2];
    FojGpuVertex before_vertices[6];
    FojStage346BmodelGpuPlan plan = {0}, before_plan = {0};
    size_t size = make_fixture(data, sizeof(data), 0, 0);
    memset(&shared, 0x44, sizeof(shared));
    shared.camera = kCamera;
    memset(batches, 0x73, sizeof(batches));
    memcpy(before_vertices, shared.vertices, sizeof(shared.vertices));
    memcpy(before_batches, batches, sizeof(batches));
    assert(foj_gpu_stage346_bmodel_prepare(data, size, &shared.camera,
           1280u, 720u, 256u, shared.vertices, 6u, batches, 2u, &plan) ==
           FOJ_GPU_STREAM_ARGUMENT);
    assert(memcmp(shared.vertices, before_vertices, sizeof(shared.vertices)) == 0);
    assert(memcmp(batches, before_batches, sizeof(batches)) == 0);
    assert(memcmp(&plan, &before_plan, sizeof(plan)) == 0);
}

int main(void) {
    test_two_sections_create_ordered_gpu_batches();
    test_sections_sharing_one_material_share_one_slot();
    test_multi_texture_material_is_refused_transactionally();
    test_capacity_and_camera_failures_leave_outputs_unchanged();
    test_camera_aliasing_output_is_rejected_transactionally();
    puts("Stage346 BMODEL GPU stream bridge tests passed");
    return 0;
}
