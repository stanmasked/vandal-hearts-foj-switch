#include "research_mesh.h"

/* Two spatially separated quads (four triangles), with two consecutive
 * material-section identifiers. Source geometry/UVs are invented. The
 * research gradient shader does not yet bind actual textures/materials. */
FojGpuStreamStatus foj_gpu_research_mesh(
    FojGpuVertex *vertices, size_t vertex_capacity,
    FojGpuBatch *batches, size_t batch_capacity,
    FojGpuStreamInfo *info) {
    const FojTexturedVertex input[FOJ_RESEARCH_VERTEX_COUNT]={
        /* Left quad, section 0. */
        {-.90f,-.55f,0.f,0.f,0.f},
        {-.10f,-.55f,0.f,.45f,0.f},
        {-.90f, .55f,0.f,0.f,1.f},
        {-.10f,-.55f,0.f,.45f,0.f},
        {-.10f, .55f,0.f,.45f,1.f},
        {-.90f, .55f,0.f,0.f,1.f},
        /* Right quad, section 1, distinct UV gradient region. */
        { .10f,-.55f,0.f,.55f,0.f},
        { .90f,-.55f,0.f,1.f,0.f},
        { .10f, .55f,0.f,.55f,1.f},
        { .90f,-.55f,0.f,1.f,0.f},
        { .90f, .55f,0.f,1.f,1.f},
        { .10f, .55f,0.f,.55f,1.f}
    };
    const FojTextureSection sections[FOJ_RESEARCH_BATCH_COUNT]={
        {0,6,0},
        {6,6,1}
    };
    const FojTextureCamera camera={
        0.f,0.f,0.f,2.f,0.f,0.f,1.f,0
    };
    return foj_gpu_prepare_stream(
        input,FOJ_RESEARCH_VERTEX_COUNT,
        sections,FOJ_RESEARCH_BATCH_COUNT,FOJ_RESEARCH_MATERIAL_COUNT,&camera,
        1280,720,vertices,vertex_capacity,batches,batch_capacity,info);
}
