#ifndef FOJ_STAGE343_BMODEL_SOURCE_H
#define FOJ_STAGE343_BMODEL_SOURCE_H

#include <stddef.h>
#include <stdint.h>

#define FOJ_STAGE343_MAX_MODEL_BYTES 4000000u
#define FOJ_STAGE343_MAX_SECTIONS 64u
#define FOJ_STAGE343_MAX_MATERIALS 128u
#define FOJ_STAGE343_MAX_TEXTURE_REFS 4096u
#define FOJ_STAGE343_MAX_TEXTURES_PER_MATERIAL 32u
#define FOJ_STAGE343_NO_MATERIAL UINT16_MAX

typedef struct {
    uint32_t offset;
    uint16_t length;
} FojStage343StringRef;

typedef enum {
    FOJ_STAGE343_MATERIAL_UNRESOLVED = 0,
    FOJ_STAGE343_MATERIAL_UNIQUE = 1,
    FOJ_STAGE343_MATERIAL_AMBIGUOUS = 2
} FojStage343MaterialResolution;

typedef struct {
    FojStage343StringRef name;
    FojStage343StringRef material_name;
    uint32_t vertex_count;
    uint32_t triangle_count;
    uint32_t positions_offset;
    uint32_t uvs_offset;
    uint32_t normals_offset;
    uint32_t face_normals_offset;
    uint32_t indices_offset;
    uint32_t skin_block_offset;
    uint16_t influences_per_vertex;
    uint16_t maximum_bone_index;
    uint16_t material_index;
    uint8_t has_skinning;
    uint8_t material_resolution;
    float bounds[6];
} FojStage343Section;

typedef struct {
    FojStage343StringRef name;
    uint16_t first_texture;
    uint16_t texture_count;
} FojStage343Material;

typedef struct {
    uint16_t material_index;
    FojStage343StringRef basename;
} FojStage343TextureRef;

/* The three arrays and their capacities are inputs. All counts and aggregate
 * fields are outputs. On failure, neither the arrays nor any field in out
 * is changed. String/attribute offsets refer into the caller-owned source
 * buffer, which must remain alive and byte-identical while the plan is used.
 */
typedef struct {
    FojStage343Section *sections;
    size_t section_capacity;
    size_t section_count;
    FojStage343Material *materials;
    size_t material_capacity;
    size_t material_count;
    FojStage343TextureRef *textures;
    size_t texture_capacity;
    size_t texture_count;
    uint32_t total_vertices;
    uint32_t total_triangles;
    uint8_t footer_tag;
    size_t footer_bytes;
} FojStage343ModelView;

/* Bounded, read-only inspection of the verified big-endian BMODEL mesh and
 * material tables. Footer semantics, transforms and skinning application are
 * deliberately not interpreted. A valid model can report unresolved or
 * ambiguous shape-to-material links; callers must fail closed before drawing.
 */
int foj_stage343_bmodel_inspect(const uint8_t *data, size_t size,
                                FojStage343ModelView *out);
int foj_stage343_string_equals(const uint8_t *data, size_t size,
                               FojStage343StringRef ref,
                               const char *literal);
int foj_stage343_materials_fully_resolved(const FojStage343ModelView *model);

#endif
