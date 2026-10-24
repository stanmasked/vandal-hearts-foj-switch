#ifndef FOJ_RIGMESH_IO_H
#define FOJ_RIGMESH_IO_H
/* Private user-local FOJRM001: portable sectioned FoJ geometry, UVs and
 * normals, with optional original BMODEL bind bones and skin weights.
 * Static meshes have zero bones and every vertex must have zero influences.
 * The format is a research container produced from the user's OWN assets.
 * No game geometry is distributed in the native executable.
 */
#include <stddef.h>
#include <stdint.h>
#include "skeletal_skin.h"

enum {
    FOJ_RIGMESH_MAX_VERTICES = 20000,
    FOJ_RIGMESH_MAX_SECTIONS = 64,
    FOJ_RIGMESH_MAX_FILE_BYTES = 2000000
};

typedef struct {
    uint32_t start_vertex;
    uint32_t vertex_count;   /* triangle soup; always a multiple of 3 */
} FojRigSection;

typedef struct {
    float uv[2];
    float normal[3];
} FojRigVertexAttributes;

typedef struct {
    size_t bone_count, vertex_count, section_count;
    FojBoneTransform *bind_bones;
    FojSkinnedVertex *vertices;
    FojRigVertexAttributes *attributes;
    FojRigSection *sections;
} FojRigMesh;

typedef enum {
    FOJ_RIGMESH_OK = 0,
    FOJ_RIGMESH_ARGUMENT,
    FOJ_RIGMESH_FORMAT,
    FOJ_RIGMESH_LIMIT,
    FOJ_RIGMESH_MEMORY
} FojRigMeshStatus;

/* out must be zero-initialized or freed first. Failed loads write no assets
 * and free any partially allocated arrays; never silently reuse old output.
 */
FojRigMeshStatus foj_rigmesh_parse(const uint8_t *bytes, size_t len,
                                   FojRigMesh *out);
void foj_rigmesh_free(FojRigMesh *mesh);

/* Hierarchy equality is only an eligibility check for gameplay clips.
 * Matching does NOT prove original animation / bind-pose conventions.
 */
int foj_rigmesh_clip_matches(const FojRigMesh *mesh, const FojAnimClip *clip);

#endif
