#include "stage343_bmodel_source.h"

#include <math.h>
#include <stdint.h>
#include <string.h>

#define STAGE343_SKIN_TAG 0x0fu
#define STAGE343_FOOTER_A 0x0au
#define STAGE343_FOOTER_B 0x0cu
#define STAGE343_MAX_FLOAT_ABS 1000000.0f
#define STAGE343_MAX_BOUND_ABS 10000000.0f

#if FOJ_STAGE343_MAX_TEXTURE_REFS > 65535u
#error "texture reference indices must fit the public format"
#endif

typedef struct {
    const uint8_t *data;
    size_t size;
    size_t pos;
} Stage343Reader;

typedef struct {
    FojStage343Section sections[FOJ_STAGE343_MAX_SECTIONS];
    FojStage343Material materials[FOJ_STAGE343_MAX_MATERIALS];
    FojStage343TextureRef textures[FOJ_STAGE343_MAX_TEXTURE_REFS];
    size_t section_count;
    size_t material_count;
    size_t texture_count;
    uint32_t total_vertices;
    uint32_t total_triangles;
    uint8_t footer_tag;
    size_t footer_bytes;
} Stage343Parsed;

static int span_overlaps(const void *left, size_t left_size,
                         const void *right, size_t right_size) {
    uintptr_t a, b;
    if (left_size == 0u || right_size == 0u) return 0;
    if (left == NULL || right == NULL) return 1;
    a = (uintptr_t)left;
    b = (uintptr_t)right;
    if (left_size > UINTPTR_MAX - a || right_size > UINTPTR_MAX - b)
        return 1;
    return a < b + right_size && b < a + left_size;
}

static int take(Stage343Reader *r, size_t amount, const uint8_t **out) {
    if (r == NULL || r->pos > r->size || amount > r->size - r->pos) return 0;
    if (out != NULL) *out = r->data + r->pos;
    r->pos += amount;
    return 1;
}

static int read_u8(Stage343Reader *r, uint8_t *out) {
    const uint8_t *p;
    if (out == NULL || !take(r, 1u, &p)) return 0;
    *out = p[0];
    return 1;
}

static int read_be16(Stage343Reader *r, uint16_t *out) {
    const uint8_t *p;
    if (out == NULL || !take(r, 2u, &p)) return 0;
    *out = (uint16_t)(((uint16_t)p[0] << 8) | (uint16_t)p[1]);
    return 1;
}

static int read_be32(Stage343Reader *r, uint32_t *out) {
    const uint8_t *p;
    if (out == NULL || !take(r, 4u, &p)) return 0;
    *out = ((uint32_t)p[0] << 24) | ((uint32_t)p[1] << 16) |
           ((uint32_t)p[2] << 8) | (uint32_t)p[3];
    return 1;
}

static int read_float(Stage343Reader *r, float *out) {
    uint32_t bits;
    if (out == NULL || sizeof(float) != sizeof(bits) ||
        !read_be32(r, &bits)) return 0;
    memcpy(out, &bits, sizeof(bits));
    return isfinite(*out) != 0;
}

static int expect_bytes(Stage343Reader *r, const uint8_t *expected,
                        size_t amount) {
    const uint8_t *p;
    if (!take(r, amount, &p)) return 0;
    return memcmp(p, expected, amount) == 0;
}

static int read_string(Stage343Reader *r, int short_length,
                       FojStage343StringRef *out) {
    uint16_t length;
    size_t offset;
    if (r == NULL || out == NULL) return 0;
    if (short_length) {
        uint8_t n;
        if (!read_u8(r, &n)) return 0;
        length = n;
    } else if (!read_be16(r, &length)) {
        return 0;
    }
    if (length == 0u || length > 255u) return 0;
    offset = r->pos;
    if (offset > UINT32_MAX || offset > r->size ||
        length > r->size - offset) return 0;
    for (size_t i = 0u; i < length; ++i) {
        uint8_t ch = r->data[offset + i];
        if (ch < 32u || ch > 126u) return 0;
    }
    r->pos += length;
    out->offset = (uint32_t)offset;
    out->length = length;
    return 1;
}

static int string_refs_equal(const uint8_t *data, size_t size,
                             FojStage343StringRef a,
                             FojStage343StringRef b) {
    if (data == NULL || a.offset > size || b.offset > size ||
        a.length > size - a.offset || b.length > size - b.offset ||
        a.length != b.length) return 0;
    return memcmp(data + a.offset, data + b.offset, a.length) == 0;
}

int foj_stage343_string_equals(const uint8_t *data, size_t size,
                               FojStage343StringRef ref,
                               const char *literal) {
    size_t length;
    if (data == NULL || literal == NULL || ref.offset > size ||
        ref.length > size - ref.offset) return 0;
    length = strlen(literal);
    if (length != ref.length) return 0;
    return memcmp(data + ref.offset, literal, length) == 0;
}

static int read_array_header(Stage343Reader *r, uint8_t expected_tag,
                             uint16_t expected_count, uint16_t *count,
                             uint32_t *payload_offset) {
    uint8_t tag;
    uint16_t n;
    if (!read_u8(r, &tag) || tag != expected_tag || !read_be16(r, &n) ||
        n == 0u || (expected_count != 0u && n != expected_count) ||
        r->pos > UINT32_MAX) return 0;
    if (count != NULL) *count = n;
    if (payload_offset != NULL) *payload_offset = (uint32_t)r->pos;
    return 1;
}

static int read_float_array(Stage343Reader *r, uint16_t count,
                            unsigned dimensions, int normal_vectors,
                            float abs_limit) {
    if (dimensions < 1u || dimensions > 3u) return 0;
    for (uint32_t i = 0u; i < (uint32_t)count; ++i) {
        float v[3] = {0.0f, 0.0f, 0.0f};
        float squared = 0.0f;
        for (unsigned d = 0u; d < dimensions; ++d) {
            if (!read_float(r, &v[d]) || fabsf(v[d]) > abs_limit) return 0;
            squared += v[d] * v[d];
        }
        if (normal_vectors && squared >= 1.0e-10f &&
            fabsf(squared - 1.0f) > 0.04f) return 0;
    }
    return 1;
}

static int read_indices(Stage343Reader *r, uint16_t count) {
    for (uint32_t i = 0u; i < (uint32_t)count; ++i) {
        uint16_t value;
        if (!read_be16(r, &value) || value != i) return 0;
    }
    return 1;
}

static int read_skin_block(Stage343Reader *r, uint16_t vertices,
                           FojStage343Section *section) {
    uint8_t tag;
    uint16_t total, influences;
    if (r->pos >= r->size || r->data[r->pos] != STAGE343_SKIN_TAG) return 1;
    if (r->pos > UINT32_MAX) return 0;
    section->skin_block_offset = (uint32_t)r->pos;
    if (!read_u8(r, &tag) || tag != STAGE343_SKIN_TAG ||
        !read_be16(r, &total) || !read_be16(r, &influences) ||
        influences == 0u || influences > 16u ||
        (uint32_t)vertices * (uint32_t)influences != (uint32_t)total)
        return 0;
    section->has_skinning = 1u;
    section->influences_per_vertex = influences;
    section->maximum_bone_index = 0u;
    for (uint32_t v = 0u; v < (uint32_t)vertices; ++v) {
        float sum = 0.0f;
        for (uint16_t j = 0u; j < influences; ++j) {
            uint16_t bone;
            float weight;
            if (!read_be16(r, &bone) || !read_float(r, &weight) ||
                weight < -0.001f || weight > 1.001f) return 0;
            if (bone > section->maximum_bone_index)
                section->maximum_bone_index = bone;
            sum += weight;
        }
        if (!isfinite(sum) || fabsf(sum - 1.0f) > 0.001f) return 0;
    }
    return 1;
}

static int parse_model(const uint8_t *data, size_t size,
                       Stage343Parsed *parsed) {
    static const uint8_t preamble[] = {0x0bu, 0x09u, 0x00u};
    static const uint8_t shape_tag[] = {0x01u, 0x20u, 0x00u};
    static const uint8_t uv_prefix[] = {0x00u, 0x03u};
    Stage343Reader r = {data, size, 0u};
    uint8_t shape_count;
    if (data == NULL || parsed == NULL || size < 50u ||
        size > FOJ_STAGE343_MAX_MODEL_BYTES ||
        !expect_bytes(&r, preamble, sizeof(preamble)) ||
        !read_u8(&r, &shape_count) || shape_count == 0u ||
        shape_count > FOJ_STAGE343_MAX_SECTIONS) return 0;

    parsed->section_count = shape_count;
    for (size_t i = 0u; i < parsed->section_count; ++i) {
        FojStage343Section *s = &parsed->sections[i];
        uint16_t vertices, attribute_count;
        uint8_t tag;
        memset(s, 0, sizeof(*s));
        s->skin_block_offset = UINT32_MAX;
        s->material_index = FOJ_STAGE343_NO_MATERIAL;
        if (i != 0u && (!read_u8(&r, &tag) || tag != 0x07u)) return 0;
        if (!expect_bytes(&r, shape_tag, sizeof(shape_tag)) ||
            !read_string(&r, 1, &s->name) ||
            !read_array_header(&r, 0x02u, 0u, &vertices,
                               &s->positions_offset) ||
            vertices % 3u != 0u ||
            !read_float_array(&r, vertices, 3u, 0, STAGE343_MAX_FLOAT_ABS))
            return 0;
        s->vertex_count = vertices;
        s->triangle_count = (uint32_t)vertices / 3u;
        if (!read_array_header(&r, 0x05u, vertices, &attribute_count, NULL) ||
            !expect_bytes(&r, uv_prefix, sizeof(uv_prefix)) ||
            r.pos > UINT32_MAX) return 0;
        s->uvs_offset = (uint32_t)r.pos;
        if (!read_float_array(&r, attribute_count, 2u, 0,
                              STAGE343_MAX_FLOAT_ABS) ||
            !read_array_header(&r, 0x10u, vertices, &attribute_count,
                               &s->normals_offset) ||
            !read_float_array(&r, attribute_count, 3u, 1,
                              STAGE343_MAX_FLOAT_ABS) ||
            !read_array_header(&r, 0x15u, (uint16_t)(vertices / 3u),
                               &attribute_count, &s->face_normals_offset) ||
            !read_float_array(&r, attribute_count, 3u, 0,
                              STAGE343_MAX_FLOAT_ABS) ||
            !read_array_header(&r, 0x04u, vertices, &attribute_count,
                               &s->indices_offset) ||
            !read_indices(&r, attribute_count) ||
            !read_skin_block(&r, vertices, s)) return 0;
        if (!read_u8(&r, &tag) || tag != 0x14u ||
            !read_string(&r, 0, &s->material_name) ||
            !read_u8(&r, &tag) || tag != 0x21u) return 0;
        for (size_t b = 0u; b < 6u; ++b) {
            if (!read_float(&r, &s->bounds[b]) ||
                fabsf(s->bounds[b]) >= STAGE343_MAX_BOUND_ABS) return 0;
        }
        if (parsed->total_vertices > UINT32_MAX - s->vertex_count ||
            parsed->total_triangles > UINT32_MAX - s->triangle_count) return 0;
        parsed->total_vertices += s->vertex_count;
        parsed->total_triangles += s->triangle_count;
    }

    {
        uint8_t tag;
        if (!read_u8(&r, &tag) || tag != 0x07u) return 0;
    }
    while (r.pos < r.size && r.data[r.pos] == 0x06u) {
        FojStage343Material *m;
        uint16_t count;
        uint8_t tag;
        if (parsed->material_count >= FOJ_STAGE343_MAX_MATERIALS ||
            !read_u8(&r, &tag) || tag != 0x06u) return 0;
        m = &parsed->materials[parsed->material_count];
        memset(m, 0, sizeof(*m));
        if (!read_string(&r, 0, &m->name) || !read_be16(&r, &count) ||
            count > FOJ_STAGE343_MAX_TEXTURES_PER_MATERIAL ||
            parsed->texture_count + count > FOJ_STAGE343_MAX_TEXTURE_REFS)
            return 0;
        m->first_texture = (uint16_t)parsed->texture_count;
        m->texture_count = count;
        for (uint16_t t = 0u; t < count; ++t) {
            FojStage343TextureRef *texture =
                &parsed->textures[parsed->texture_count];
            texture->material_index = (uint16_t)parsed->material_count;
            if (!read_string(&r, 0, &texture->basename)) return 0;
            ++parsed->texture_count;
        }
        ++parsed->material_count;
    }
    if (parsed->material_count == 0u || r.pos >= r.size ||
        (r.data[r.pos] != STAGE343_FOOTER_A &&
         r.data[r.pos] != STAGE343_FOOTER_B)) return 0;
    parsed->footer_tag = r.data[r.pos];
    parsed->footer_bytes = r.size - r.pos;

    for (size_t i = 0u; i < parsed->section_count; ++i) {
        FojStage343Section *s = &parsed->sections[i];
        size_t matches = 0u;
        for (size_t m = 0u; m < parsed->material_count; ++m) {
            if (string_refs_equal(data, size, s->material_name,
                                  parsed->materials[m].name)) {
                s->material_index = (uint16_t)m;
                ++matches;
            }
        }
        if (matches == 1u) {
            s->material_resolution = FOJ_STAGE343_MATERIAL_UNIQUE;
        } else if (matches > 1u) {
            s->material_index = FOJ_STAGE343_NO_MATERIAL;
            s->material_resolution = FOJ_STAGE343_MATERIAL_AMBIGUOUS;
        } else {
            s->material_index = FOJ_STAGE343_NO_MATERIAL;
            s->material_resolution = FOJ_STAGE343_MATERIAL_UNRESOLVED;
        }
    }
    return 1;
}

int foj_stage343_bmodel_inspect(const uint8_t *data, size_t size,
                                FojStage343ModelView *out) {
    Stage343Parsed parsed;
    size_t section_bytes, material_bytes, texture_bytes;
    if (data == NULL || out == NULL ||
        span_overlaps(data, size, out, sizeof(*out))) return 0;
    memset(&parsed, 0, sizeof(parsed));
    if (!parse_model(data, size, &parsed)) return 0;
    if (parsed.section_count > out->section_capacity ||
        parsed.material_count > out->material_capacity ||
        parsed.texture_count > out->texture_capacity ||
        (parsed.section_count != 0u && out->sections == NULL) ||
        (parsed.material_count != 0u && out->materials == NULL) ||
        (parsed.texture_count != 0u && out->textures == NULL)) return 0;
    section_bytes = parsed.section_count * sizeof(parsed.sections[0]);
    material_bytes = parsed.material_count * sizeof(parsed.materials[0]);
    texture_bytes = parsed.texture_count * sizeof(parsed.textures[0]);
    if (span_overlaps(out, sizeof(*out), out->sections, section_bytes) ||
        span_overlaps(out, sizeof(*out), out->materials, material_bytes) ||
        span_overlaps(out, sizeof(*out), out->textures, texture_bytes) ||
        span_overlaps(data, size, out->sections, section_bytes) ||
        span_overlaps(data, size, out->materials, material_bytes) ||
        span_overlaps(data, size, out->textures, texture_bytes) ||
        span_overlaps(out->sections, section_bytes,
                      out->materials, material_bytes) ||
        span_overlaps(out->sections, section_bytes,
                      out->textures, texture_bytes) ||
        span_overlaps(out->materials, material_bytes,
                      out->textures, texture_bytes)) return 0;

    if (section_bytes != 0u)
        memcpy(out->sections, parsed.sections, section_bytes);
    if (material_bytes != 0u)
        memcpy(out->materials, parsed.materials, material_bytes);
    if (texture_bytes != 0u)
        memcpy(out->textures, parsed.textures, texture_bytes);
    out->section_count = parsed.section_count;
    out->material_count = parsed.material_count;
    out->texture_count = parsed.texture_count;
    out->total_vertices = parsed.total_vertices;
    out->total_triangles = parsed.total_triangles;
    out->footer_tag = parsed.footer_tag;
    out->footer_bytes = parsed.footer_bytes;
    return 1;
}

int foj_stage343_materials_fully_resolved(const FojStage343ModelView *model) {
    if (model == NULL || model->section_count == 0u ||
        model->sections == NULL || model->materials == NULL) return 0;
    for (size_t i = 0u; i < model->section_count; ++i) {
        const FojStage343Section *s = &model->sections[i];
        if (s->material_resolution != FOJ_STAGE343_MATERIAL_UNIQUE ||
            s->material_index >= model->material_count) return 0;
    }
    return 1;
}
