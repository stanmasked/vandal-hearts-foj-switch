#include "stage344_bmodel_rig.h"

#include <math.h>
#include <stdint.h>
#include <string.h>

#define STAGE344_RIG_TAG 0x0au
#define STAGE344_NO_RIG_TAG 0x0cu
#define STAGE344_RIG_END_TAG 0x0cu
#define STAGE344_MAX_TRANSFORM_ABS 1000000.0f

typedef struct {
    const uint8_t *data;
    size_t size;
    size_t pos;
} Stage344Reader;

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

static int read_u16(Stage344Reader *r, uint16_t *out) {
    if (r == NULL || out == NULL || r->pos > r->size ||
        r->size - r->pos < 2u) return 0;
    *out = (uint16_t)(((uint16_t)r->data[r->pos] << 8) |
                      (uint16_t)r->data[r->pos + 1u]);
    r->pos += 2u;
    return 1;
}

static int read_float(Stage344Reader *r, float *out) {
    uint32_t bits;
    if (r == NULL || out == NULL || r->pos > r->size ||
        r->size - r->pos < 4u) return 0;
    bits = ((uint32_t)r->data[r->pos] << 24) |
           ((uint32_t)r->data[r->pos + 1u] << 16) |
           ((uint32_t)r->data[r->pos + 2u] << 8) |
           (uint32_t)r->data[r->pos + 3u];
    r->pos += 4u;
    memcpy(out, &bits, sizeof(bits));
    return isfinite(*out) != 0;
}

static int validate_rig_footer(const uint8_t *footer, size_t length,
                               FojStage344RigSummary *summary) {
    Stage344Reader r = {footer, length, 0u};
    uint8_t tag;
    uint16_t count;
    if (footer == NULL || summary == NULL || length == 0u) return 0;
    tag = footer[0];
    if (tag == STAGE344_NO_RIG_TAG) {
        if (length != 1u) return 0;
        summary->has_rig = 0u;
        summary->bone_count = 0u;
        summary->root_count = 0u;
        return 1;
    }
    if (tag != STAGE344_RIG_TAG || length < 36u) return 0;
    ++r.pos;
    if (!read_u16(&r, &count) || count == 0u ||
        count > FOJ_STAGE344_MAX_BONES || length != 4u + 32u * (size_t)count ||
        footer[length - 1u] != STAGE344_RIG_END_TAG) return 0;
    summary->has_rig = 1u;
    summary->bone_count = count;
    summary->root_count = 0u;
    for (uint16_t i = 0u; i < count; ++i) {
        uint16_t parent, metadata;
        float q[4], translation[3];
        float norm_squared = 0.0f;
        if (!read_u16(&r, &parent) || !read_u16(&r, &metadata)) return 0;
        (void)metadata;
        if (parent == UINT16_MAX) {
            ++summary->root_count;
        } else if (parent >= i) {
            return 0;
        }
        for (size_t j = 0u; j < 4u; ++j) {
            if (!read_float(&r, &q[j])) return 0;
            norm_squared += q[j] * q[j];
        }
        if (fabsf(norm_squared - 1.0f) > 0.04f) return 0;
        for (size_t j = 0u; j < 3u; ++j) {
            if (!read_float(&r, &translation[j]) ||
                fabsf(translation[j]) >= STAGE344_MAX_TRANSFORM_ABS) return 0;
        }
    }
    if (r.pos != length - 1u || footer[r.pos] != STAGE344_RIG_END_TAG)
        return 0;
    return 1;
}

int foj_stage344_bmodel_rig_validate(const uint8_t *data, size_t size,
                                     const FojStage343ModelView *model,
                                     FojStage344RigSummary *out) {
    FojStage344RigSummary parsed;
    size_t footer_offset;
    if (data == NULL || model == NULL || out == NULL ||
        size > FOJ_STAGE343_MAX_MODEL_BYTES ||
        model->section_count == 0u ||
        model->section_count > FOJ_STAGE343_MAX_SECTIONS ||
        model->sections == NULL || model->footer_bytes == 0u ||
        model->footer_bytes > size ||
        overlaps(data, size, out, sizeof(*out)) ||
        overlaps(model, sizeof(*model), out, sizeof(*out)) ||
        overlaps(model->sections, model->section_count * sizeof(model->sections[0]),
                 out, sizeof(*out))) return 0;
    memset(&parsed, 0, sizeof(parsed));
    parsed.skin_indices_in_range = 1u;
    footer_offset = size - model->footer_bytes;
    if (data[footer_offset] != model->footer_tag ||
        !validate_rig_footer(data + footer_offset, model->footer_bytes, &parsed))
        return 0;

    for (size_t i = 0u; i < model->section_count; ++i) {
        const FojStage343Section *section = &model->sections[i];
        if (section->has_skinning != 0u) {
            ++parsed.skinned_section_count;
            if (section->influences_per_vertex == 0u ||
                section->influences_per_vertex > 16u) return 0;
            if (parsed.has_rig == 0u ||
                section->maximum_bone_index >= parsed.bone_count) {
                ++parsed.out_of_range_skinned_sections;
                parsed.skin_indices_in_range = 0u;
            }
        } else if (section->influences_per_vertex != 0u) {
            return 0;
        }
    }
    *out = parsed;
    return 1;
}

int foj_stage344_skinning_bones_in_range(const FojStage344RigSummary *summary) {
    return summary != NULL && summary->skin_indices_in_range != 0u;
}
