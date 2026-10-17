#include "research_mesh.h"

/* Two triangles share an edge but use independent triangle-soup vertices.
 * Source positions and UVs are invented: they exercise exactly the shared
 * projection/batch preparation that later decoded geometry will use. */
FojGpuStreamStatus foj_gpu_research_mesh(
    FojGpuVertex *vertices, size_t vertex_capacity,
    FojGpuBatch *batches, size_t batch_capacity,
    FojGpuStreamInfo *info) {
    const FojTexturedVertex input[FOJ_RESEARCH_VERTEX_COUNT]={
        {-.65f,-.50f,0.f,0.f,0.f},
        { .65f,-.50f,0.f,1.f,0.f},
        {-.65f, .50f,0.f,0.f,1.f},
        { .65f,-.50f,0.f,1.f,0.f},
        { .65f, .50f,0.f,1.f,1.f},
        {-.65f, .50f,0.f,0.f,1.f}
    };
    const FojTextureSection sections[FOJ_RESEARCH_BATCH_COUNT]={
        {0,FOJ_RESEARCH_VERTEX_COUNT,0}
    };
    const FojTextureCamera camera={
        0.f,0.f,0.f,2.f,0.f,0.f,1.f,0
    };
    return foj_gpu_prepare_stream(
        input,FOJ_RESEARCH_VERTEX_COUNT,
        sections,FOJ_RESEARCH_BATCH_COUNT,1,&camera,
        1280,720,vertices,vertex_capacity,batches,batch_capacity,info);
}
