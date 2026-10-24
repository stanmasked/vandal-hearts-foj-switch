#include "stage345_bmodel_mesh_bridge.h"

#include "../core/skeletal_skin.h"

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

static int empty_output(const FojStage345BmodelMesh *out) {
    return out != NULL &&
        out->mesh.bone_count == 0u && out->mesh.vertex_count == 0u &&
        out->mesh.section_count == 0u && out->mesh.bind_bones == NULL &&
        out->mesh.vertices == NULL && out->mesh.attributes == NULL &&
        out->mesh.sections == NULL && out->section_material_indices == NULL &&
        out->materials == NULL && out->textures == NULL &&
        out->material_count == 0u && out->texture_count == 0u &&
        out->source_data == NULL && out->source_size == 0u &&
        out->footer_tag == 0u && out->footer_bytes == 0u;
}

void foj_stage345_bmodel_mesh_free(FojStage345BmodelMesh *mesh) {
    if (mesh == NULL) return;
    foj_rigmesh_free(&mesh->mesh);
    free(mesh->section_material_indices);
    free(mesh->materials);
    free(mesh->textures);
    memset(mesh, 0, sizeof(*mesh));
}

static int read_u16_at(const uint8_t *data, size_t size,
                       size_t offset, uint16_t *out) {
    if (data == NULL || out == NULL || offset > size ||
        size - offset < 2u) return 0;
    *out = (uint16_t)(((uint16_t)data[offset] << 8) |
                      (uint16_t)data[offset + 1u]);
    return 1;
}

static int read_float_at(const uint8_t *data, size_t size,
                         size_t offset, float *out) {
    uint32_t bits;
    if (data == NULL || out == NULL || sizeof(float) != sizeof(bits) ||
        offset > size || size - offset < 4u) return 0;
    bits = ((uint32_t)data[offset] << 24) |
           ((uint32_t)data[offset + 1u] << 16) |
           ((uint32_t)data[offset + 2u] << 8) |
           (uint32_t)data[offset + 3u];
    memcpy(out, &bits, sizeof(bits));
    return isfinite(*out) != 0;
}

static int read_float_index(const uint8_t *data, size_t size,
                            uint32_t base, size_t index, float *out) {
    size_t offset = (size_t)base;
    if (index > (SIZE_MAX - offset) / 4u) return 0;
    offset += index * 4u;
    return read_float_at(data, size, offset, out);
}

static void free_view(FojStage343ModelView *view) {
    if (view == NULL) return;
    free(view->sections);
    free(view->materials);
    free(view->textures);
    memset(view, 0, sizeof(*view));
}

static int allocate_mesh(FojStage345BmodelMesh *mesh,
                         size_t bones, size_t vertices, size_t sections) {
    mesh->mesh.bone_count = bones;
    mesh->mesh.vertex_count = vertices;
    mesh->mesh.section_count = sections;
    mesh->mesh.bind_bones = calloc(bones, sizeof(*mesh->mesh.bind_bones));
    mesh->mesh.vertices = calloc(vertices, sizeof(*mesh->mesh.vertices));
    mesh->mesh.attributes = calloc(vertices, sizeof(*mesh->mesh.attributes));
    mesh->mesh.sections = calloc(sections, sizeof(*mesh->mesh.sections));
    mesh->section_material_indices =
        calloc(sections, sizeof(*mesh->section_material_indices));
    if (mesh->mesh.bind_bones == NULL || mesh->mesh.vertices == NULL ||
        mesh->mesh.attributes == NULL || mesh->mesh.sections == NULL ||
        mesh->section_material_indices == NULL) return 0;
    return 1;
}

static int parse_bind_bones(const uint8_t *data, size_t size,
                            size_t footer_offset, size_t footer_bytes,
                            size_t expected_bones, FojBoneTransform *bones) {
    uint16_t count;
    if (data == NULL || bones == NULL || footer_offset > size ||
        footer_bytes > size - footer_offset || footer_bytes < 4u ||
        data[footer_offset] != 0x0au ||
        !read_u16_at(data, size, footer_offset + 1u, &count) ||
        count != expected_bones ||
        footer_bytes != 4u + 32u * (size_t)count) return 0;
    for (size_t i = 0u; i < count; ++i) {
        const size_t base = footer_offset + 3u + 32u * i;
        uint16_t parent;
        if (!read_u16_at(data, size, base, &parent)) return 0;
        bones[i].parent = parent == UINT16_MAX ? -1 : (int)parent;
        for (size_t j = 0u; j < 4u; ++j) {
            if (!read_float_at(data, size, base + 4u + j * 4u,
                               &bones[i].rotation_xyzw[j])) return 0;
        }
        for (size_t j = 0u; j < 3u; ++j) {
            if (!read_float_at(data, size, base + 20u + j * 4u,
                               &bones[i].translation_xyz[j])) return 0;
        }
    }
    return 1;
}

static FojStage345Status copy_section(const uint8_t *data, size_t size,
                                      const FojStage343Section *src,
                                      size_t vertex_start, size_t bone_count,
                                      FojRigMesh *mesh) {
    size_t influence_offset = 0u;
    uint16_t total = 0u, influences = 0u;
    if (vertex_start > mesh->vertex_count ||
        src->vertex_count == 0u ||
        src->vertex_count > mesh->vertex_count - vertex_start ||
        src->vertex_count % 3u != 0u) return FOJ_STAGE345_FORMAT;
    if (src->influences_per_vertex > FOJ_SKIN_MAX_INFLUENCES)
        return FOJ_STAGE345_SKIN;
    if (src->has_skinning != 0u) {
        if (src->skin_block_offset == UINT32_MAX ||
            src->skin_block_offset > size ||
            size - src->skin_block_offset < 5u ||
            data[src->skin_block_offset] != 0x0fu ||
            !read_u16_at(data, size, (size_t)src->skin_block_offset + 1u,
                         &total) ||
            !read_u16_at(data, size, (size_t)src->skin_block_offset + 3u,
                         &influences) ||
            influences == 0u || influences != src->influences_per_vertex ||
            (uint32_t)src->vertex_count * (uint32_t)influences != total)
            return FOJ_STAGE345_SKIN;
        influence_offset = (size_t)src->skin_block_offset + 5u;
    } else if (src->influences_per_vertex != 0u) {
        return FOJ_STAGE345_SKIN;
    }

    for (size_t v = 0u; v < src->vertex_count; ++v) {
        FojSkinnedVertex *vertex = &mesh->vertices[vertex_start + v];
        FojRigVertexAttributes *attributes = &mesh->attributes[vertex_start + v];
        for (size_t axis = 0u; axis < 3u; ++axis) {
            if (!read_float_index(data, size, src->positions_offset,
                                  v * 3u + axis, &vertex->xyz[axis]) ||
                !read_float_index(data, size, src->normals_offset,
                                  v * 3u + axis, &attributes->normal[axis]))
                return FOJ_STAGE345_FORMAT;
        }
        for (size_t axis = 0u; axis < 2u; ++axis) {
            if (!read_float_index(data, size, src->uvs_offset,
                                  v * 2u + axis, &attributes->uv[axis]))
                return FOJ_STAGE345_FORMAT;
        }
        vertex->influence_count = src->influences_per_vertex;
        for (unsigned j = 0u; j < vertex->influence_count; ++j) {
            uint16_t bone;
            float weight;
            if (influence_offset > size || size - influence_offset < 6u ||
                !read_u16_at(data, size, influence_offset, &bone) ||
                !read_float_at(data, size, influence_offset + 2u, &weight) ||
                bone >= bone_count || !isfinite(weight) ||
                weight < 0.0f || weight > 1.001f)
                return FOJ_STAGE345_SKIN;
            vertex->influences[j].bone = bone;
            vertex->influences[j].weight = weight;
            influence_offset += 6u;
        }
        if (vertex->influence_count != 0u) {
            float total_weight = 0.0f;
            for (unsigned j = 0u; j < vertex->influence_count; ++j)
                total_weight += vertex->influences[j].weight;
            if (!isfinite(total_weight) ||
                fabsf(total_weight - 1.0f) > 0.002f)
                return FOJ_STAGE345_SKIN;
        }
    }
    if (src->has_skinning != 0u &&
        influence_offset != (size_t)src->skin_block_offset + 5u +
                           (size_t)src->vertex_count *
                           src->influences_per_vertex * 6u)
        return FOJ_STAGE345_SKIN;
    return FOJ_STAGE345_OK;
}

FojStage345Status foj_stage345_bmodel_to_rigmesh(
    const uint8_t *data, size_t size, FojStage345BmodelMesh *out) {
    FojStage343ModelView view;
    FojStage344RigSummary rig;
    FojStage345BmodelMesh parsed;
    FojStage345Status status = FOJ_STAGE345_FORMAT;
    size_t vertex_cursor = 0u;
    size_t footer_offset;
    if (data == NULL || out == NULL || size > FOJ_STAGE343_MAX_MODEL_BYTES ||
        !empty_output(out) || overlaps(data, size, out, sizeof(*out)))
        return FOJ_STAGE345_ARGUMENT;
    memset(&view, 0, sizeof(view));
    memset(&rig, 0, sizeof(rig));
    memset(&parsed, 0, sizeof(parsed));

    view.sections = calloc(FOJ_STAGE343_MAX_SECTIONS, sizeof(*view.sections));
    view.materials = calloc(FOJ_STAGE343_MAX_MATERIALS, sizeof(*view.materials));
    view.textures = calloc(FOJ_STAGE343_MAX_TEXTURE_REFS, sizeof(*view.textures));
    if (view.sections == NULL || view.materials == NULL || view.textures == NULL) {
        status = FOJ_STAGE345_MEMORY;
        goto done;
    }
    view.section_capacity = FOJ_STAGE343_MAX_SECTIONS;
    view.material_capacity = FOJ_STAGE343_MAX_MATERIALS;
    view.texture_capacity = FOJ_STAGE343_MAX_TEXTURE_REFS;
    if (!foj_stage343_bmodel_inspect(data, size, &view)) {
        status = FOJ_STAGE345_FORMAT;
        goto done;
    }
    if (!foj_stage343_materials_fully_resolved(&view)) {
        status = FOJ_STAGE345_MATERIAL;
        goto done;
    }
    if (!foj_stage344_bmodel_rig_validate(data, size, &view, &rig) ||
        rig.has_rig == 0u || rig.bone_count == 0u) {
        status = FOJ_STAGE345_RIG;
        goto done;
    }
    if (!foj_stage344_skinning_bones_in_range(&rig)) {
        status = FOJ_STAGE345_SKIN;
        goto done;
    }
    if (view.total_vertices < 3u ||
        view.total_vertices > FOJ_RIGMESH_MAX_VERTICES ||
        view.section_count == 0u ||
        view.section_count > FOJ_RIGMESH_MAX_SECTIONS ||
        rig.bone_count > FOJ_SKIN_MAX_BONES) {
        status = FOJ_STAGE345_LIMIT;
        goto done;
    }
    for (size_t i = 0u; i < view.section_count; ++i) {
        if (view.sections[i].influences_per_vertex > FOJ_SKIN_MAX_INFLUENCES) {
            status = FOJ_STAGE345_SKIN;
            goto done;
        }
    }
    if (!allocate_mesh(&parsed, rig.bone_count, view.total_vertices,
                       view.section_count)) {
        status = FOJ_STAGE345_MEMORY;
        goto done;
    }
    footer_offset = size - view.footer_bytes;
    if (!parse_bind_bones(data, size, footer_offset, view.footer_bytes,
                          rig.bone_count, parsed.mesh.bind_bones)) {
        status = FOJ_STAGE345_RIG;
        goto done;
    }
    for (size_t i = 0u; i < view.section_count; ++i) {
        FojStage343Section *section = &view.sections[i];
        FojRigSection *native_section = &parsed.mesh.sections[i];
        if (section->material_index >= view.material_count) {
            status = FOJ_STAGE345_MATERIAL;
            goto done;
        }
        native_section->start_vertex = (uint32_t)vertex_cursor;
        native_section->vertex_count = section->vertex_count;
        parsed.section_material_indices[i] = section->material_index;
        status = copy_section(data, size, section, vertex_cursor,
                              rig.bone_count, &parsed.mesh);
        if (status != FOJ_STAGE345_OK) goto done;
        vertex_cursor += section->vertex_count;
    }
    if (vertex_cursor != parsed.mesh.vertex_count) {
        status = FOJ_STAGE345_FORMAT;
        goto done;
    }

    parsed.materials = view.materials;
    parsed.textures = view.textures;
    parsed.material_count = view.material_count;
    parsed.texture_count = view.texture_count;
    parsed.source_data = data;
    parsed.source_size = size;
    parsed.footer_tag = view.footer_tag;
    parsed.footer_bytes = view.footer_bytes;
    view.materials = NULL;
    view.textures = NULL;
    *out = parsed;
    memset(&parsed, 0, sizeof(parsed));
    status = FOJ_STAGE345_OK;

done:
    free_view(&view);
    foj_stage345_bmodel_mesh_free(&parsed);
    return status;
}

int foj_stage345_mesh_integrity_ready(const FojStage345BmodelMesh *mesh) {
    if (mesh == NULL || mesh->source_data == NULL ||
        mesh->source_size == 0u || mesh->mesh.bind_bones == NULL ||
        mesh->mesh.vertices == NULL || mesh->mesh.attributes == NULL ||
        mesh->mesh.sections == NULL || mesh->section_material_indices == NULL ||
        mesh->materials == NULL || mesh->mesh.bone_count == 0u ||
        mesh->mesh.bone_count > FOJ_SKIN_MAX_BONES ||
        mesh->mesh.vertex_count < 3u ||
        mesh->mesh.vertex_count > FOJ_RIGMESH_MAX_VERTICES ||
        mesh->mesh.section_count == 0u ||
        mesh->mesh.section_count > FOJ_RIGMESH_MAX_SECTIONS ||
        mesh->material_count == 0u ||
        mesh->material_count > FOJ_STAGE343_MAX_MATERIALS ||
        mesh->texture_count > FOJ_STAGE343_MAX_TEXTURE_REFS ||
        mesh->textures == NULL) return 0;

    for (size_t i = 0u; i < mesh->mesh.bone_count; ++i) {
        const FojBoneTransform *bone = &mesh->mesh.bind_bones[i];
        float norm = 0.0f;
        if (bone->parent < -1 ||
            (bone->parent >= 0 && (size_t)bone->parent >= i)) return 0;
        for (size_t j = 0u; j < 4u; ++j) {
            if (!isfinite(bone->rotation_xyzw[j])) return 0;
            norm += bone->rotation_xyzw[j] * bone->rotation_xyzw[j];
        }
        if (!isfinite(norm) || fabsf(norm - 1.0f) > 0.04f) return 0;
        for (size_t j = 0u; j < 3u; ++j)
            if (!isfinite(bone->translation_xyz[j]) ||
                fabsf(bone->translation_xyz[j]) >= 1000000.0f) return 0;
    }

    for (size_t i = 0u; i < mesh->material_count; ++i) {
        const FojStage343Material *material = &mesh->materials[i];
        if (material->name.offset > mesh->source_size ||
            material->name.length > mesh->source_size - material->name.offset ||
            material->first_texture > mesh->texture_count ||
            material->texture_count > mesh->texture_count - material->first_texture)
            return 0;
        for (size_t j = 0u; j < material->texture_count; ++j) {
            const FojStage343TextureRef *texture =
                &mesh->textures[(size_t)material->first_texture + j];
            if (texture->material_index != i ||
                texture->basename.offset > mesh->source_size ||
                texture->basename.length >
                    mesh->source_size - texture->basename.offset) return 0;
        }
    }

    size_t covered = 0u;
    for (size_t i = 0u; i < mesh->mesh.section_count; ++i) {
        const FojRigSection *section = &mesh->mesh.sections[i];
        if (mesh->section_material_indices[i] >= mesh->material_count ||
            section->start_vertex != covered ||
            section->vertex_count == 0u ||
            section->vertex_count % 3u != 0u ||
            section->start_vertex > mesh->mesh.vertex_count ||
            section->vertex_count > mesh->mesh.vertex_count - section->start_vertex)
            return 0;
        covered += section->vertex_count;
    }
    if (covered != mesh->mesh.vertex_count) return 0;

    for (size_t i = 0u; i < mesh->mesh.vertex_count; ++i) {
        const FojSkinnedVertex *vertex = &mesh->mesh.vertices[i];
        float total_weight = 0.0f;
        if (vertex->influence_count > FOJ_SKIN_MAX_INFLUENCES) return 0;
        for (size_t axis = 0u; axis < 3u; ++axis) {
            if (!isfinite(vertex->xyz[axis]) ||
                fabsf(vertex->xyz[axis]) > 1000000.0f ||
                !isfinite(mesh->mesh.attributes[i].normal[axis]) ||
                fabsf(mesh->mesh.attributes[i].normal[axis]) > 1000000.0f)
                return 0;
        }
        for (size_t axis = 0u; axis < 2u; ++axis)
            if (!isfinite(mesh->mesh.attributes[i].uv[axis]) ||
                fabsf(mesh->mesh.attributes[i].uv[axis]) > 1000000.0f)
                return 0;
        for (unsigned j = 0u; j < vertex->influence_count; ++j) {
            const FojSkinInfluence *influence = &vertex->influences[j];
            if (influence->bone >= mesh->mesh.bone_count ||
                !isfinite(influence->weight) ||
                influence->weight < 0.0f || influence->weight > 1.001f)
                return 0;
            total_weight += influence->weight;
        }
        if (vertex->influence_count != 0u &&
            (!isfinite(total_weight) || fabsf(total_weight - 1.0f) > 0.002f))
            return 0;
    }
    return 1;
}
