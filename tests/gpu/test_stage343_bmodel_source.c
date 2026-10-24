#include "stage343_bmodel_source.h"

#include <assert.h>
#include <math.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

typedef struct {
    uint8_t *data;
    size_t capacity;
    size_t size;
} Writer;

static void put8(Writer *w, uint8_t value) {
    assert(w->size < w->capacity);
    w->data[w->size++] = value;
}

static void put16(Writer *w, uint16_t value) {
    put8(w, (uint8_t)(value >> 8));
    put8(w, (uint8_t)value);
}

static void put_float(Writer *w, float value) {
    uint32_t bits;
    memcpy(&bits, &value, sizeof(bits));
    put8(w, (uint8_t)(bits >> 24));
    put8(w, (uint8_t)(bits >> 16));
    put8(w, (uint8_t)(bits >> 8));
    put8(w, (uint8_t)bits);
}

static void put_string8(Writer *w, const char *text) {
    size_t n = strlen(text);
    assert(n > 0u && n <= 255u);
    put8(w, (uint8_t)n);
    for (size_t i = 0u; i < n; ++i) put8(w, (uint8_t)text[i]);
}

static void put_string16(Writer *w, const char *text) {
    size_t n = strlen(text);
    assert(n > 0u && n <= 255u);
    put16(w, (uint16_t)n);
    for (size_t i = 0u; i < n; ++i) put8(w, (uint8_t)text[i]);
}

static void put_shape(Writer *w, const char *name, const char *material,
                      int separator, int skinned) {
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
    for (size_t i = 0u; i < 9u; ++i) put_float(w, positions[i]);
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
        for (size_t i = 0u; i < 3u; ++i) {
            put16(w, 0u); put_float(w, 0.25f);
            put16(w, 1u); put_float(w, 0.75f);
        }
    }
    put8(w, 0x14u); put_string16(w, material);
    put8(w, 0x21u);
    put_float(w, 0.0f); put_float(w, 0.0f); put_float(w, 0.0f);
    put_float(w, 1.0f); put_float(w, 1.0f); put_float(w, 0.0f);
}

static size_t make_fixture(uint8_t *data, size_t capacity) {
    Writer w = {data, capacity, 0u};
    put8(&w, 0x0bu); put8(&w, 0x09u); put8(&w, 0x00u); put8(&w, 2u);
    put_shape(&w, "meshA", "matA", 0, 1);
    put_shape(&w, "meshB", "matB", 1, 0);
    put8(&w, 0x07u);
    put8(&w, 0x06u); put_string16(&w, "matA"); put16(&w, 1u);
    put_string16(&w, "texA.tga");
    put8(&w, 0x06u); put_string16(&w, "matB"); put16(&w, 1u);
    put_string16(&w, "texB.tga");
    put8(&w, 0x0cu); put8(&w, 0x12u); put8(&w, 0x34u); put8(&w, 0x56u);
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

static void test_successful_multisection_parse(void) {
    uint8_t data[4096];
    FojStage343Section sections[FOJ_STAGE343_MAX_SECTIONS];
    FojStage343Material materials[FOJ_STAGE343_MAX_MATERIALS];
    FojStage343TextureRef textures[FOJ_STAGE343_MAX_TEXTURE_REFS];
    FojStage343ModelView view;
    size_t size = make_fixture(data, sizeof(data));
    init_view(&view, sections, FOJ_STAGE343_MAX_SECTIONS,
              materials, FOJ_STAGE343_MAX_MATERIALS,
              textures, FOJ_STAGE343_MAX_TEXTURE_REFS);
    assert(foj_stage343_bmodel_inspect(data, size, &view));
    assert(view.section_count == 2u && view.material_count == 2u);
    assert(view.texture_count == 2u && view.total_vertices == 6u);
    assert(view.total_triangles == 2u && view.footer_tag == 0x0cu);
    assert(view.footer_bytes == 4u);
    assert(foj_stage343_string_equals(data, size, sections[0].name, "meshA"));
    assert(foj_stage343_string_equals(data, size, sections[1].name, "meshB"));
    assert(sections[0].vertex_count == 3u && sections[0].triangle_count == 1u);
    assert(sections[0].positions_offset < sections[0].uvs_offset);
    assert(sections[0].uvs_offset < sections[0].normals_offset);
    assert(sections[0].normals_offset < sections[0].face_normals_offset);
    assert(sections[0].face_normals_offset < sections[0].indices_offset);
    assert(sections[0].has_skinning == 1u);
    assert(sections[0].influences_per_vertex == 2u);
    assert(sections[0].maximum_bone_index == 1u);
    assert(sections[1].has_skinning == 0u);
    assert(sections[1].skin_block_offset == UINT32_MAX);
    assert(sections[0].material_resolution == FOJ_STAGE343_MATERIAL_UNIQUE);
    assert(sections[0].material_index == 0u && sections[1].material_index == 1u);
    assert(foj_stage343_materials_fully_resolved(&view));
    assert(materials[0].texture_count == 1u && materials[1].texture_count == 1u);
    assert(foj_stage343_string_equals(data, size, textures[0].basename, "texA.tga"));
    assert(foj_stage343_string_equals(data, size, textures[1].basename, "texB.tga"));
}

static void test_rejects_bad_indices_and_preserves_output(void) {
    uint8_t data[4096];
    FojStage343Section good_sections[FOJ_STAGE343_MAX_SECTIONS];
    FojStage343Material good_materials[FOJ_STAGE343_MAX_MATERIALS];
    FojStage343TextureRef good_textures[FOJ_STAGE343_MAX_TEXTURE_REFS];
    FojStage343ModelView good;
    FojStage343Section sections[FOJ_STAGE343_MAX_SECTIONS];
    FojStage343Material materials[FOJ_STAGE343_MAX_MATERIALS];
    FojStage343TextureRef textures[FOJ_STAGE343_MAX_TEXTURE_REFS];
    FojStage343Section before_sections[FOJ_STAGE343_MAX_SECTIONS];
    FojStage343Material before_materials[FOJ_STAGE343_MAX_MATERIALS];
    FojStage343TextureRef before_textures[FOJ_STAGE343_MAX_TEXTURE_REFS];
    FojStage343ModelView view;
    size_t size = make_fixture(data, sizeof(data));
    init_view(&good, good_sections, FOJ_STAGE343_MAX_SECTIONS,
              good_materials, FOJ_STAGE343_MAX_MATERIALS,
              good_textures, FOJ_STAGE343_MAX_TEXTURE_REFS);
    assert(foj_stage343_bmodel_inspect(data, size, &good));
    data[good_sections[0].indices_offset + 1u] = 1u;
    memset(sections, 0xa5, sizeof(sections));
    memset(materials, 0x5a, sizeof(materials));
    memset(textures, 0x3c, sizeof(textures));
    memcpy(before_sections, sections, sizeof(sections));
    memcpy(before_materials, materials, sizeof(materials));
    memcpy(before_textures, textures, sizeof(textures));
    init_view(&view, sections, FOJ_STAGE343_MAX_SECTIONS,
              materials, FOJ_STAGE343_MAX_MATERIALS,
              textures, FOJ_STAGE343_MAX_TEXTURE_REFS);
    view.section_count = 71u; view.material_count = 72u; view.texture_count = 73u;
    view.total_vertices = 74u; view.total_triangles = 75u;
    view.footer_tag = 0xacu; view.footer_bytes = 76u;
    assert(!foj_stage343_bmodel_inspect(data, size, &view));
    assert(memcmp(before_sections, sections, sizeof(sections)) == 0);
    assert(memcmp(before_materials, materials, sizeof(materials)) == 0);
    assert(memcmp(before_textures, textures, sizeof(textures)) == 0);
    assert(view.section_count == 71u && view.material_count == 72u);
    assert(view.texture_count == 73u && view.total_vertices == 74u);
    assert(view.total_triangles == 75u && view.footer_tag == 0xacu);
    assert(view.footer_bytes == 76u);
}

static void test_skin_weight_failure_and_truncation(void) {
    uint8_t data[4096];
    FojStage343Section sections[FOJ_STAGE343_MAX_SECTIONS];
    FojStage343Material materials[FOJ_STAGE343_MAX_MATERIALS];
    FojStage343TextureRef textures[FOJ_STAGE343_MAX_TEXTURE_REFS];
    FojStage343ModelView view;
    size_t size = make_fixture(data, sizeof(data));
    init_view(&view, sections, FOJ_STAGE343_MAX_SECTIONS,
              materials, FOJ_STAGE343_MAX_MATERIALS,
              textures, FOJ_STAGE343_MAX_TEXTURE_REFS);
    assert(foj_stage343_bmodel_inspect(data, size, &view));
    data[sections[0].skin_block_offset + 10u] = 0x66u;
    data[sections[0].skin_block_offset + 9u] = 0x66u;
    data[sections[0].skin_block_offset + 8u] = 0x66u;
    data[sections[0].skin_block_offset + 7u] = 0x3fu;
    init_view(&view, sections, FOJ_STAGE343_MAX_SECTIONS,
              materials, FOJ_STAGE343_MAX_MATERIALS,
              textures, FOJ_STAGE343_MAX_TEXTURE_REFS);
    assert(!foj_stage343_bmodel_inspect(data, size, &view));
    size = make_fixture(data, sizeof(data));
    init_view(&view, sections, FOJ_STAGE343_MAX_SECTIONS,
              materials, FOJ_STAGE343_MAX_MATERIALS,
              textures, FOJ_STAGE343_MAX_TEXTURE_REFS);
    assert(!foj_stage343_bmodel_inspect(data, size - 12u, &view));
}

static void test_material_resolution_is_fail_closed(void) {
    uint8_t data[4096];
    FojStage343Section sections[FOJ_STAGE343_MAX_SECTIONS];
    FojStage343Material materials[FOJ_STAGE343_MAX_MATERIALS];
    FojStage343TextureRef textures[FOJ_STAGE343_MAX_TEXTURE_REFS];
    FojStage343ModelView view;
    size_t size = make_fixture(data, sizeof(data));
    init_view(&view, sections, FOJ_STAGE343_MAX_SECTIONS,
              materials, FOJ_STAGE343_MAX_MATERIALS,
              textures, FOJ_STAGE343_MAX_TEXTURE_REFS);
    assert(foj_stage343_bmodel_inspect(data, size, &view));
    data[sections[0].material_name.offset] = (uint8_t)'x';
    init_view(&view, sections, FOJ_STAGE343_MAX_SECTIONS,
              materials, FOJ_STAGE343_MAX_MATERIALS,
              textures, FOJ_STAGE343_MAX_TEXTURE_REFS);
    assert(foj_stage343_bmodel_inspect(data, size, &view));
    assert(sections[0].material_resolution == FOJ_STAGE343_MATERIAL_UNRESOLVED);
    assert(sections[0].material_index == FOJ_STAGE343_NO_MATERIAL);
    assert(!foj_stage343_materials_fully_resolved(&view));

    size = make_fixture(data, sizeof(data));
    init_view(&view, sections, FOJ_STAGE343_MAX_SECTIONS,
              materials, FOJ_STAGE343_MAX_MATERIALS,
              textures, FOJ_STAGE343_MAX_TEXTURE_REFS);
    assert(foj_stage343_bmodel_inspect(data, size, &view));
    memcpy(data + materials[1].name.offset, data + materials[0].name.offset,
           materials[0].name.length);
    init_view(&view, sections, FOJ_STAGE343_MAX_SECTIONS,
              materials, FOJ_STAGE343_MAX_MATERIALS,
              textures, FOJ_STAGE343_MAX_TEXTURE_REFS);
    assert(foj_stage343_bmodel_inspect(data, size, &view));
    assert(sections[0].material_resolution == FOJ_STAGE343_MATERIAL_AMBIGUOUS);
    assert(sections[0].material_index == FOJ_STAGE343_NO_MATERIAL);
    assert(!foj_stage343_materials_fully_resolved(&view));
}

static void test_capacity_and_invalid_geometry_refuse_without_writes(void) {
    uint8_t data[4096];
    FojStage343Section sections[FOJ_STAGE343_MAX_SECTIONS];
    FojStage343Material materials[FOJ_STAGE343_MAX_MATERIALS];
    FojStage343TextureRef textures[FOJ_STAGE343_MAX_TEXTURE_REFS];
    FojStage343Section before_sections[FOJ_STAGE343_MAX_SECTIONS];
    FojStage343ModelView view;
    size_t size = make_fixture(data, sizeof(data));
    memset(sections, 0x91, sizeof(sections));
    memset(materials, 0x92, sizeof(materials));
    memset(textures, 0x93, sizeof(textures));
    memcpy(before_sections, sections, sizeof(sections));
    init_view(&view, sections, 1u, materials, FOJ_STAGE343_MAX_MATERIALS,
              textures, FOJ_STAGE343_MAX_TEXTURE_REFS);
    view.section_count = 123u;
    assert(!foj_stage343_bmodel_inspect(data, size, &view));
    assert(view.section_count == 123u);
    assert(memcmp(before_sections, sections, sizeof(sections)) == 0);

    size = make_fixture(data, sizeof(data));
    init_view(&view, sections, FOJ_STAGE343_MAX_SECTIONS,
              materials, FOJ_STAGE343_MAX_MATERIALS,
              textures, FOJ_STAGE343_MAX_TEXTURE_REFS);
    assert(foj_stage343_bmodel_inspect(data, size, &view));
    data[sections[0].positions_offset] = 0x7fu;
    data[sections[0].positions_offset + 1u] = 0xc0u;
    data[sections[0].positions_offset + 2u] = 0x00u;
    data[sections[0].positions_offset + 3u] = 0x00u;
    init_view(&view, sections, FOJ_STAGE343_MAX_SECTIONS,
              materials, FOJ_STAGE343_MAX_MATERIALS,
              textures, FOJ_STAGE343_MAX_TEXTURE_REFS);
    assert(!foj_stage343_bmodel_inspect(data, size, &view));
}

int main(void) {
    test_successful_multisection_parse();
    test_rejects_bad_indices_and_preserves_output();
    test_skin_weight_failure_and_truncation();
    test_material_resolution_is_fail_closed();
    test_capacity_and_invalid_geometry_refuse_without_writes();
    puts("Stage343 BMODEL source tests passed");
    return 0;
}
