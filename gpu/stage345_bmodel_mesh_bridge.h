#ifndef FOJ_STAGE345_BMODEL_MESH_BRIDGE_H
#define FOJ_STAGE345_BMODEL_MESH_BRIDGE_H

#include "stage343_bmodel_source.h"
#include "stage344_bmodel_rig.h"
#include "../core/rigmesh_io.h"

#include <stddef.h>
#include <stdint.h>

typedef enum {
    FOJ_STAGE345_OK = 0,
    FOJ_STAGE345_ARGUMENT,
    FOJ_STAGE345_FORMAT,
    FOJ_STAGE345_LIMIT,
    FOJ_STAGE345_MEMORY,
    FOJ_STAGE345_MATERIAL,
    FOJ_STAGE345_RIG,
    FOJ_STAGE345_SKIN
} FojStage345Status;

/* A native, owned CPU representation assembled from one verified BMODEL.
 * Geometry/rig/weight arrays are owned by this object. Material and texture
 * names remain offsets into source_data; the caller must keep those original
 * bytes alive and byte-identical until this object is freed.
 *
 * The output must be zero-initialized or previously freed. On failure the
 * output remains byte-for-byte unchanged. The borrowed source_data is never
 * freed by foj_stage345_bmodel_mesh_free().
 */
typedef struct {
    FojRigMesh mesh;
    uint16_t *section_material_indices;
    FojStage343Material *materials;
    FojStage343TextureRef *textures;
    size_t material_count;
    size_t texture_count;
    const uint8_t *source_data;
    size_t source_size;
    uint8_t footer_tag;
    size_t footer_bytes;
} FojStage345BmodelMesh;

FojStage345Status foj_stage345_bmodel_to_rigmesh(
    const uint8_t *data, size_t size, FojStage345BmodelMesh *out);
void foj_stage345_bmodel_mesh_free(FojStage345BmodelMesh *mesh);

/* True only when every source section has one unambiguous material and every
 * weighted vertex references a bone in the validated rig. This is a data
 * integrity gate, not proof of the original engine's transform convention. */
int foj_stage345_mesh_integrity_ready(const FojStage345BmodelMesh *mesh);

#endif
