#include "stage344_bmodel_rig.h"

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

static void put_float(Writer *w, float v) {
    uint32_t bits;
    memcpy(&bits, &v, sizeof(bits));
    put8(w, (uint8_t)(bits >> 24));
    put8(w, (uint8_t)(bits >> 16));
    put8(w, (uint8_t)(bits >> 8));
    put8(w, (uint8_t)bits);
}

static size_t make_rig_footer(uint8_t *data, size_t capacity, uint16_t bones) {
    Writer w = {data, capacity, 0u};
    put8(&w, 0x0au);
    put16(&w, bones);
    for (uint16_t i = 0u; i < bones; ++i) {
        put16(&w, i == 0u ? UINT16_MAX : (uint16_t)(i - 1u));
        put16(&w, 0u);
        put_float(&w, 0.0f); put_float(&w, 0.0f);
        put_float(&w, 0.0f); put_float(&w, 1.0f);
        put_float(&w, 0.0f); put_float(&w, 0.0f); put_float(&w, 0.0f);
    }
    put8(&w, 0x0cu);
    return w.size;
}

static void init_model(FojStage343ModelView *model, FojStage343Section *section,
                       uint8_t footer_tag, size_t footer_bytes,
                       uint16_t max_bone, int skinned) {
    memset(model, 0, sizeof(*model));
    memset(section, 0, sizeof(*section));
    model->sections = section;
    model->section_capacity = 1u;
    model->section_count = 1u;
    model->footer_tag = footer_tag;
    model->footer_bytes = footer_bytes;
    section->has_skinning = (uint8_t)(skinned != 0);
    section->influences_per_vertex = skinned ? 2u : 0u;
    section->maximum_bone_index = max_bone;
}

static void test_valid_two_bone_rig_and_weights(void) {
    uint8_t data[128] = {0};
    FojStage343Section section;
    FojStage343ModelView model;
    FojStage344RigSummary summary;
    size_t size = make_rig_footer(data, sizeof(data), 2u);
    init_model(&model, &section, 0x0au, size, 1u, 1);
    memset(&summary, 0xa5, sizeof(summary));
    assert(foj_stage344_bmodel_rig_validate(data, size, &model, &summary));
    assert(summary.has_rig == 1u && summary.bone_count == 2u);
    assert(summary.root_count == 1u && summary.skinned_section_count == 1u);
    assert(summary.out_of_range_skinned_sections == 0u);
    assert(foj_stage344_skinning_bones_in_range(&summary));
}

static void test_out_of_range_bone_is_reported_not_clamped(void) {
    uint8_t data[128] = {0};
    FojStage343Section section;
    FojStage343ModelView model;
    FojStage344RigSummary summary;
    size_t size = make_rig_footer(data, sizeof(data), 2u);
    init_model(&model, &section, 0x0au, size, 2u, 1);
    assert(foj_stage344_bmodel_rig_validate(data, size, &model, &summary));
    assert(summary.bone_count == 2u);
    assert(summary.out_of_range_skinned_sections == 1u);
    assert(!foj_stage344_skinning_bones_in_range(&summary));
}

static void test_no_rig_is_valid_only_for_unskinned_sections(void) {
    const uint8_t no_rig[] = {0x0cu};
    FojStage343Section section;
    FojStage343ModelView model;
    FojStage344RigSummary summary;
    init_model(&model, &section, 0x0cu, sizeof(no_rig), 0u, 0);
    assert(foj_stage344_bmodel_rig_validate(no_rig, sizeof(no_rig), &model, &summary));
    assert(summary.has_rig == 0u && summary.bone_count == 0u);
    assert(foj_stage344_skinning_bones_in_range(&summary));
    section.has_skinning = 1u;
    section.influences_per_vertex = 1u;
    assert(foj_stage344_bmodel_rig_validate(no_rig, sizeof(no_rig), &model, &summary));
    assert(summary.out_of_range_skinned_sections == 1u);
    assert(!foj_stage344_skinning_bones_in_range(&summary));
}

static void test_malformed_parent_and_quaternion_fail_transactionally(void) {
    uint8_t data[128] = {0};
    FojStage343Section section;
    FojStage343ModelView model;
    FojStage344RigSummary summary, before;
    size_t size = make_rig_footer(data, sizeof(data), 2u);
    init_model(&model, &section, 0x0au, size, 1u, 1);
    memset(&summary, 0x5c, sizeof(summary));
    before = summary;
    data[35] = 0x00u; data[36] = 0x01u; /* bone 1 cannot parent itself */
    assert(!foj_stage344_bmodel_rig_validate(data, size, &model, &summary));
    assert(memcmp(&summary, &before, sizeof(summary)) == 0);

    size = make_rig_footer(data, sizeof(data), 2u);
    data[19] = 0x40u; data[20] = 0x00u;
    data[21] = 0x00u; data[22] = 0x00u; /* non-unit root quaternion */
    assert(!foj_stage344_bmodel_rig_validate(data, size, &model, &summary));
    assert(memcmp(&summary, &before, sizeof(summary)) == 0);
}

static void test_footer_length_count_terminator_and_metadata_are_checked(void) {
    uint8_t data[128] = {0};
    FojStage343Section section;
    FojStage343ModelView model;
    FojStage344RigSummary summary;
    size_t size = make_rig_footer(data, sizeof(data), 2u);
    init_model(&model, &section, 0x0au, size, 1u, 1);
    data[size - 1u] = 0x0du;
    assert(!foj_stage344_bmodel_rig_validate(data, size, &model, &summary));
    size = make_rig_footer(data, sizeof(data), 2u);
    data[1] = 0u; data[2] = 0u;
    assert(!foj_stage344_bmodel_rig_validate(data, size, &model, &summary));
    size = make_rig_footer(data, sizeof(data), 2u);
    model.footer_tag = 0x0cu;
    assert(!foj_stage344_bmodel_rig_validate(data, size, &model, &summary));
    model.footer_tag = 0x0au;
    model.footer_bytes = size - 1u;
    assert(!foj_stage344_bmodel_rig_validate(data, size, &model, &summary));
}

int main(void) {
    test_valid_two_bone_rig_and_weights();
    test_out_of_range_bone_is_reported_not_clamped();
    test_no_rig_is_valid_only_for_unskinned_sections();
    test_malformed_parent_and_quaternion_fail_transactionally();
    test_footer_length_count_terminator_and_metadata_are_checked();
    puts("Stage344 BMODEL rig/skin tests passed");
    return 0;
}
