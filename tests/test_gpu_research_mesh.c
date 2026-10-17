/* SDK-free bridge regression: synthetic triangle soup -> GPU upload stream. */
#ifdef NDEBUG
#undef NDEBUG
#endif
#include <assert.h>
#include <math.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include "research_mesh.h"

int main(void) {
    FojGpuVertex vertices[FOJ_RESEARCH_VERTEX_COUNT];
    FojGpuBatch batches[FOJ_RESEARCH_BATCH_COUNT];
    FojGpuStreamInfo info;
    memset(vertices,0xA5,sizeof(vertices));
    memset(batches,0xA5,sizeof(batches));
    memset(&info,0xA5,sizeof(info));
    FojGpuVertex original_vertices[FOJ_RESEARCH_VERTEX_COUNT];
    FojGpuBatch original_batches[FOJ_RESEARCH_BATCH_COUNT];
    FojGpuStreamInfo original_info;
    memcpy(original_vertices,vertices,sizeof(vertices));
    memcpy(original_batches,batches,sizeof(batches));
    memcpy(&original_info,&info,sizeof(info));

    /* Invalid capacities must not partially overwrite the upload buffers. */
    assert(foj_gpu_research_mesh(vertices,FOJ_RESEARCH_VERTEX_COUNT-1,
             batches,FOJ_RESEARCH_BATCH_COUNT,&info)==FOJ_GPU_STREAM_BOUNDS);
    assert(!memcmp(vertices,original_vertices,sizeof(vertices)));
    assert(!memcmp(batches,original_batches,sizeof(batches)));
    assert(!memcmp(&info,&original_info,sizeof(info)));
    assert(foj_gpu_research_mesh(vertices,FOJ_RESEARCH_VERTEX_COUNT,
             batches,0,&info)==FOJ_GPU_STREAM_BOUNDS);
    assert(!memcmp(vertices,original_vertices,sizeof(vertices)));
    assert(!memcmp(batches,original_batches,sizeof(batches)));
    assert(foj_gpu_research_mesh(NULL,FOJ_RESEARCH_VERTEX_COUNT,
             batches,FOJ_RESEARCH_BATCH_COUNT,&info)==FOJ_GPU_STREAM_ARGUMENT);

    assert(foj_gpu_research_mesh(vertices,FOJ_RESEARCH_VERTEX_COUNT,
             batches,FOJ_RESEARCH_BATCH_COUNT,&info)==FOJ_GPU_STREAM_OK);
    assert(info.vertices_written==FOJ_RESEARCH_VERTEX_COUNT);
    assert(info.batches_written==FOJ_RESEARCH_BATCH_COUNT);
    assert(batches[0].first_vertex==0);
    assert(batches[0].vertex_count==FOJ_RESEARCH_VERTEX_COUNT);
    assert(batches[0].texture_index==0);
    assert(fabsf(info.camera_depth_max-info.camera_depth_min)<1e-6f);
    for (size_t i=0;i<FOJ_RESEARCH_VERTEX_COUNT;i++) {
        assert(isfinite(vertices[i].x)&&isfinite(vertices[i].y));
        assert(vertices[i].z>=0.f&&vertices[i].z<=1.f);
        assert(vertices[i].w==1.f);
        assert(vertices[i].u>=0.f&&vertices[i].u<=1.f);
        assert(vertices[i].v>=0.f&&vertices[i].v<=1.f);
    }
    /* Shared-edge positions/UVs must agree after the shared projection. */
    assert(!memcmp(&vertices[1],&vertices[3],sizeof(FojGpuVertex)));
    assert(!memcmp(&vertices[2],&vertices[5],sizeof(FojGpuVertex)));
    assert(vertices[0].x<vertices[1].x);
    assert(vertices[0].y<vertices[2].y);
    puts("GPU synthetic six-vertex research mesh: PASS");
    return 0;
}
