#include "stage345_bmodel_mesh_bridge.h"
#include "../core/skeletal_skin.h"

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
                      int separator, int skinned, unsigned influences,
                      float x_offset) {
    static const float base_positions[9] = {
        0.0f, 0.0f, 0.0f, 1.0f, 0.0f, 0.0f, 0.0f, 1.0f, 0.0f
    };
    static const float uvs[6] = {0.0f, 0.0f, 1.0f, 0.0f, 0.0f, 1.0f};
    static const float normals[9] = {
        0.0f, 0.0f, 1.0f, 0.0f, 0.0f, 1.0f, 0.0f, 0.0f, 1.0f
    };
    static const float face_normal[3] = {0.0f, 0.0f, -1.0f};
    static const float weights6[6] = {0.2f, 0.2f, 0.2f, 0.2f, 0.1f, 0.1f};
    if (separator) put8(w, 0x07u);
    put8(w, 0x01u); put8(w, 0x20u); put8(w, 0x00u);
    put_string8(w, name);
    put8(w, 0x02u); put16(w, 3u);
    for (size_t i = 0u; i < 9u; ++i)
        put_float(w, base_positions[i] + (i % 3u == 0u ? x_offset : 0.0f));
    put8(w, 0x05u); put16(w, 3u); put8(w, 0x00u); put8(w, 0x03u);
    for (size_t i = 0u; i < 6u; ++i) put_float(w, uvs[i]);
    put8(w, 0x10u); put16(w, 3u);
    for (size_t i = 0u; i < 9u; ++i) put_float(w, normals[i]);
    put8(w, 0x15u); put16(w, 1u);
    for (size_t i = 0u; i < 3u; ++i) put_float(w, face_normal[i]);
    put8(w, 0x04u); put16(w, 3u);
    put16(w, 0u); put16(w, 1u); put16(w, 2u);
    if (skinned) {
        assert(influences > 0u && influences <= 6u);
        put8(w, 0x0fu); put16(w, (uint16_t)(3u * influences));
        put16(w, (uint16_t)influences);
        for (size_t v = 0u; v < 3u; ++v) {
            for (unsigned j = 0u; j < influences; ++j) {
                put16(w, (uint16_t)(j % 2u));
                put_float(w, influences == 2u ? (j == 0u ? 0.25f : 0.75f) :
                          weights6[j]);
            }
        }
    }
    put8(w, 0x14u); put_string16(w, material);
    put8(w, 0x21u);
    put_float(w, x_offset); put_float(w, 0.0f); put_float(w, 0.0f);
    put_float(w, x_offset + 1.0f); put_float(w, 1.0f); put_float(w, 0.0f);
}

static void put_rig(Writer *w, uint16_t count) {
    put8(w, 0x0au); put16(w, count);
    for (uint16_t i = 0u; i < count; ++i) {
        put16(w, i == 0u ? UINT16_MAX : (uint16_t)(i - 1u));
        put16(w, 0u);
        put_float(w, 0.0f); put_float(w, 0.0f);
        put_float(w, 0.0f); put_float(w, 1.0f);
        put_float(w, 0.0f);
        put_float(w, i == 0u ? 0.0f : 2.0f);
        put_float(w, 0.0f);
    }
    put8(w, 0x0cu);
}

static size_t make_fixture(uint8_t *data, size_t capacity,
                           unsigned influences) {
    Writer w = {data, capacity, 0u};
    put8(&w, 0x0bu); put8(&w, 0x09u); put8(&w, 0x00u); put8(&w, 2u);
    put_shape(&w, "meshA", "matA", 0, 1, influences, 0.0f);
    put_shape(&w, "meshB", "matB", 1, 0, 0u, 2.0f);
    put8(&w, 0x07u);
    put8(&w, 0x06u); put_string16(&w, "matA"); put16(&w, 1u);
    put_string16(&w, "texA.tga");
    put8(&w, 0x06u); put_string16(&w, "matB"); put16(&w, 1u);
    put_string16(&w, "texB.tga");
    put_rig(&w, 2u);
    return w.size;
}

static void init_view(FojStage343ModelView *view,
                      FojStage343Section *sections, size_t section_capacity,
                      FojStage343Material *materials, size_t material_capacity,
                      FojStage343TextureRef *textures, size_t texture_capacity) {
    memset(view, 0, sizeof(*view));
    view->sections = sections;
    view->section_capacity = section_capacity;
    view->materials = materials;
    view->material_capacity = material_capacity;
    view->textures = textures;
    view->texture_capacity = texture_capacity;
}

static void test_bridge_preserves_multisection_geometry_skin_and_materials(void) {
    uint8_t data[4096];
    FojStage345BmodelMesh mesh;
    size_t size = make_fixture(data, sizeof(data), 2u);
    memset(&mesh, 0, sizeof(mesh));
    assert(foj_stage345_bmodel_to_rigmesh(data, size, &mesh) == FOJ_STAGE345_OK);
    assert(mesh.mesh.bone_count == 2u && mesh.mesh.vertex_count == 6u);
    assert(mesh.mesh.section_count == 2u && mesh.material_count == 2u);
    assert(mesh.texture_count == 2u && mesh.source_data == data);
    assert(mesh.source_size == size && mesh.footer_tag == 0x0au);
    assert(mesh.mesh.sections[0].start_vertex == 0u);
    assert(mesh.mesh.sections[0].vertex_count == 3u);
    assert(mesh.mesh.sections[1].start_vertex == 3u);
    assert(mesh.mesh.sections[1].vertex_count == 3u);
    assert(mesh.section_material_indices[0] == 0u);
    assert(mesh.section_material_indices[1] == 1u);
    assert(mesh.mesh.bind_bones[0].parent == -1);
    assert(mesh.mesh.bind_bones[1].parent == 0);
    assert(mesh.mesh.bind_bones[1].translation_xyz[1] == 2.0f);
    assert(mesh.mesh.vertices[0].influence_count == 2u);
    assert(mesh.mesh.vertices[0].influences[0].bone == 0u);
    assert(mesh.mesh.vertices[0].influences[1].bone == 1u);
    assert(mesh.mesh.vertices[0].influences[0].weight == 0.25f);
    assert(mesh.mesh.vertices[0].influences[1].weight == 0.75f);
    assert(mesh.mesh.vertices[3].influence_count == 0u);
    assert(mesh.mesh.vertices[0].xyz[0] == 0.0f);
    assert(mesh.mesh.vertices[3].xyz[0] == 2.0f);
    assert(mesh.mesh.attributes[1].uv[0] == 1.0f);
    assert(mesh.mesh.attributes[2].normal[2] == 1.0f);
    assert(foj_stage343_string_equals(data, size, mesh.materials[0].name, "matA"));
    assert(foj_stage343_string_equals(data, size, mesh.textures[1].basename, "texB.tga"));
    assert(foj_stage345_mesh_integrity_ready(&mesh));
    foj_stage345_bmodel_mesh_free(&mesh);
    assert(mesh.mesh.vertices == NULL && mesh.mesh.bone_count == 0u);
}

static void test_bind_pose_skinning_keeps_positions_unchanged(void) {
    uint8_t data[4096];
    FojStage345BmodelMesh mesh;
    FojSkinMatrix palette[FOJ_SKIN_MAX_BONES];
    float output[18];
    size_t size = make_fixture(data, sizeof(data), 2u);
    memset(&mesh, 0, sizeof(mesh));
    assert(foj_stage345_bmodel_to_rigmesh(data, size, &mesh) == FOJ_STAGE345_OK);
    assert(foj_skin_build_palette(mesh.mesh.bind_bones, mesh.mesh.bind_bones,
                                  mesh.mesh.bone_count, palette,
                                  FOJ_SKIN_MAX_BONES) == FOJ_SKIN_OK);
    assert(foj_skin_deform(mesh.mesh.vertices, mesh.mesh.vertex_count, palette,
                           mesh.mesh.bone_count, output, 18u) == FOJ_SKIN_OK);
    for (size_t i = 0u; i < mesh.mesh.vertex_count; ++i)
        for (size_t axis = 0u; axis < 3u; ++axis)
            assert(output[i * 3u + axis] == mesh.mesh.vertices[i].xyz[axis]);
    foj_stage345_bmodel_mesh_free(&mesh);
}

static void test_invalid_bone_index_refuses_without_partial_output(void) {
    uint8_t data[4096];
    FojStage343Section sections[FOJ_STAGE343_MAX_SECTIONS];
    FojStage343Material materials[FOJ_STAGE343_MAX_MATERIALS];
    FojStage343TextureRef textures[FOJ_STAGE343_MAX_TEXTURE_REFS];
    FojStage343ModelView view;
    FojStage345BmodelMesh mesh, before;
    size_t size = make_fixture(data, sizeof(data), 2u);
    init_view(&view, sections, FOJ_STAGE343_MAX_SECTIONS, materials,
              FOJ_STAGE343_MAX_MATERIALS, textures, FOJ_STAGE343_MAX_TEXTURE_REFS);
    assert(foj_stage343_bmodel_inspect(data, size, &view));
    data[sections[0].skin_block_offset + 5u] = 0u;
    data[sections[0].skin_block_offset + 6u] = 2u;
    memset(&mesh, 0, sizeof(mesh));
    before = mesh;
    assert(foj_stage345_bmodel_to_rigmesh(data, size, &mesh) == FOJ_STAGE345_SKIN);
    assert(memcmp(&mesh, &before, sizeof(mesh)) == 0);
}

static void test_ambiguous_material_refuses_without_partial_output(void) {
    uint8_t data[4096];
    FojStage343Section sections[FOJ_STAGE343_MAX_SECTIONS];
    FojStage343Material materials[FOJ_STAGE343_MAX_MATERIALS];
    FojStage343TextureRef textures[FOJ_STAGE343_MAX_TEXTURE_REFS];
    FojStage343ModelView view;
    FojStage345BmodelMesh mesh, before;
    size_t size = make_fixture(data, sizeof(data), 2u);
    init_view(&view, sections, FOJ_STAGE343_MAX_SECTIONS, materials,
              FOJ_STAGE343_MAX_MATERIALS, textures, FOJ_STAGE343_MAX_TEXTURE_REFS);
    assert(foj_stage343_bmodel_inspect(data, size, &view));
    memcpy(data + materials[1].name.offset, data + materials[0].name.offset,
           materials[0].name.length);
    memset(&mesh, 0, sizeof(mesh));
    before = mesh;
    assert(foj_stage345_bmodel_to_rigmesh(data, size, &mesh) == FOJ_STAGE345_MATERIAL);
    assert(memcmp(&mesh, &before, sizeof(mesh)) == 0);
}

static void test_more_than_five_influences_and_truncation_are_rejected(void) {
    uint8_t data[4096];
    FojStage345BmodelMesh mesh, before;
    size_t size = make_fixture(data, sizeof(data), 6u);
    memset(&mesh, 0, sizeof(mesh));
    before = mesh;
    assert(foj_stage345_bmodel_to_rigmesh(data, size, &mesh) == FOJ_STAGE345_SKIN);
    assert(memcmp(&mesh, &before, sizeof(mesh)) == 0);

    size = make_fixture(data, sizeof(data), 2u);
    assert(foj_stage345_bmodel_to_rigmesh(data, size - 3u, &mesh) ==
           FOJ_STAGE345_RIG);
    assert(memcmp(&mesh, &before, sizeof(mesh)) == 0);
}

static void test_nonempty_output_is_rejected_unchanged(void) {
    uint8_t data[4096];
    FojStage345BmodelMesh mesh, before;
    size_t size = make_fixture(data, sizeof(data), 2u);
    memset(&mesh, 0, sizeof(mesh));
    mesh.source_size = 99u;
    before = mesh;
    assert(foj_stage345_bmodel_to_rigmesh(data, size, &mesh) ==
           FOJ_STAGE345_ARGUMENT);
    assert(memcmp(&mesh, &before, sizeof(mesh)) == 0);
}

int main(void) {
    test_bridge_preserves_multisection_geometry_skin_and_materials();
    test_bind_pose_skinning_keeps_positions_unchanged();
    test_invalid_bone_index_refuses_without_partial_output();
    test_ambiguous_material_refuses_without_partial_output();
    test_more_than_five_influences_and_truncation_are_rejected();
    test_nonempty_output_is_rejected_unchanged();
    puts("Stage345 BMODEL native mesh bridge tests passed");
    return 0;
}
