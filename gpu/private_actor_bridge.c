#include "private_actor_bridge.h"

#include <stdlib.h>
#include <string.h>
#include "rigmesh_io.h"
#include "material_table.h"

/* The parsed formats are intentionally not GPU uploadable on their own:
 * validate every section/material before projecting a bind-pose snapshot. */
FojGpuStreamStatus foj_gpu_private_actor_prepare(
    const uint8_t *mesh_bytes,size_t mesh_len,
    const uint8_t *material_bytes,size_t material_len,
    const FojTextureCamera *camera,unsigned width,unsigned height,
    size_t gpu_alignment,
    FojGpuVertex *vertices_out,size_t vertex_capacity,
    FojGpuBatch *batches_out,size_t batch_capacity,
    FojGpuPrivateActorPlan *plan) {
    if (!mesh_bytes || !material_bytes || !camera || !vertices_out ||
        !batches_out || !plan)
        return FOJ_GPU_STREAM_ARGUMENT;

    /* Reject impossible sizes before any heap allocations or parsing. */
    if (mesh_len<28 || mesh_len>FOJ_RIGMESH_MAX_FILE_BYTES ||
        material_len<20 || material_len>16u+4u*FOJ_MAT_MAX_SECTIONS)
        return FOJ_GPU_STREAM_BOUNDS;

    FojRigMesh mesh={0};
    FojMaterialTable material={0};
    FojGpuStreamStatus result=FOJ_GPU_STREAM_INVALID;
    if (foj_rigmesh_parse(mesh_bytes,mesh_len,&mesh)!=FOJ_RIGMESH_OK)
        goto done;
    if (foj_material_table_parse(material_bytes,material_len,&material)!=0)
        goto done;
    if (mesh.section_count!=material.section_count ||
        mesh.section_count>FOJ_GPU_MAX_BATCHES ||
        material.texture_count>FOJ_GPU_MAX_TEXTURES ||
        vertex_capacity<mesh.vertex_count ||
        batch_capacity<mesh.section_count) {
        result=FOJ_GPU_STREAM_BOUNDS;
        goto done;
    }

    FojTextureSection sections[FOJ_GPU_MAX_BATCHES];
    FojGpuBatch checked_batches[FOJ_GPU_MAX_BATCHES];
    for (size_t i=0;i<mesh.section_count;++i) {
        sections[i]=(FojTextureSection){
            mesh.sections[i].start_vertex,
            mesh.sections[i].vertex_count,
            material.section_texture[i]
        };
        checked_batches[i]=(FojGpuBatch){
            mesh.sections[i].start_vertex,
            mesh.sections[i].vertex_count,
            material.section_texture[i]
        };
    }
    FojGpuActorUploadPlan upload={0};
    result=foj_gpu_actor_upload_plan(
        checked_batches,mesh.section_count,mesh.vertex_count,
        material.texture_count,gpu_alignment,&upload);
    if (result!=FOJ_GPU_STREAM_OK)goto done;
    const uint32_t expected_mask=
        (UINT32_C(1)<<(unsigned)material.texture_count)-UINT32_C(1);
    if (upload.material_mask!=expected_mask) {
        result=FOJ_GPU_STREAM_INVALID;
        goto done;
    }

    /* Scratch is capped by FOJ_RIGMESH_MAX_VERTICES; never allocate the
     * potentially proprietary input payload a second time. No originals
     * are persisted or written into executable images. */
    FojTexturedVertex *source=malloc(
        mesh.vertex_count*sizeof(FojTexturedVertex));
    if (!source) {
        result=FOJ_GPU_STREAM_BOUNDS;
        goto done;
    }
    for (size_t i=0;i<mesh.vertex_count;++i) {
        source[i]=(FojTexturedVertex){
            mesh.vertices[i].xyz[0],
            mesh.vertices[i].xyz[1],
            mesh.vertices[i].xyz[2],
            mesh.attributes[i].uv[0],
            mesh.attributes[i].uv[1]
        };
    }
    FojGpuStreamInfo staged={0};
    /* Projection validates all vertices, camera and sections before
     * modifying output arrays, so rejected input is transactional. */
    result=foj_gpu_prepare_stream(
        source,mesh.vertex_count,sections,mesh.section_count,
        material.texture_count,camera,width,height,
        vertices_out,vertex_capacity,batches_out,batch_capacity,&staged);
    free(source);
    if (result==FOJ_GPU_STREAM_OK) {
        const FojGpuPrivateActorPlan completed={staged,upload};
        *plan=completed;
    }
done:
    foj_rigmesh_free(&mesh);
    return result;
}
