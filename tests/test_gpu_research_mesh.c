/* SDK-free bridge: two synthetic GPU batches and transactional draw plans. */
#ifdef NDEBUG
#undef NDEBUG
#endif
#include <assert.h>
#include <math.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include "research_mesh.h"
#include "gpu_draw_plan.h"

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

    assert(foj_gpu_research_mesh(vertices,FOJ_RESEARCH_VERTEX_COUNT-1,
             batches,FOJ_RESEARCH_BATCH_COUNT,&info)==FOJ_GPU_STREAM_BOUNDS);
    assert(!memcmp(vertices,original_vertices,sizeof(vertices)));
    assert(!memcmp(batches,original_batches,sizeof(batches)));
    assert(!memcmp(&info,&original_info,sizeof(info)));
    assert(foj_gpu_research_mesh(vertices,FOJ_RESEARCH_VERTEX_COUNT,
             batches,FOJ_RESEARCH_BATCH_COUNT-1,&info)==FOJ_GPU_STREAM_BOUNDS);
    assert(!memcmp(vertices,original_vertices,sizeof(vertices)));
    assert(!memcmp(batches,original_batches,sizeof(batches)));
    assert(foj_gpu_research_mesh(NULL,FOJ_RESEARCH_VERTEX_COUNT,
             batches,FOJ_RESEARCH_BATCH_COUNT,&info)==FOJ_GPU_STREAM_ARGUMENT);

    assert(foj_gpu_research_mesh(vertices,FOJ_RESEARCH_VERTEX_COUNT,
             batches,FOJ_RESEARCH_BATCH_COUNT,&info)==FOJ_GPU_STREAM_OK);
    assert(info.vertices_written==FOJ_RESEARCH_VERTEX_COUNT);
    assert(info.batches_written==FOJ_RESEARCH_BATCH_COUNT);
    assert(batches[0].first_vertex==0 && batches[0].vertex_count==6);
    assert(batches[1].first_vertex==6 && batches[1].vertex_count==6);
    assert(batches[0].texture_index==0 && batches[1].texture_index==1);
    assert(fabsf(info.camera_depth_max-info.camera_depth_min)<1e-6f);
    for (size_t i=0;i<FOJ_RESEARCH_VERTEX_COUNT;i++) {
        assert(isfinite(vertices[i].x)&&isfinite(vertices[i].y));
        assert(vertices[i].z>=0.f&&vertices[i].z<=1.f);
        assert(vertices[i].w==1.f);
        assert(vertices[i].u>=0.f&&vertices[i].u<=1.f);
        assert(vertices[i].v>=0.f&&vertices[i].v<=1.f);
    }
    /* Both quads have consistent duplicated triangle-soup shared edges. */
    for(size_t i=0;i<FOJ_RESEARCH_VERTEX_COUNT;i+=6) {
        assert(!memcmp(&vertices[i+1],&vertices[i+3],sizeof(FojGpuVertex)));
        assert(!memcmp(&vertices[i+2],&vertices[i+5],sizeof(FojGpuVertex)));
        assert(vertices[i].x<vertices[i+1].x);
        assert(vertices[i].y<vertices[i+2].y);
    }
    assert(vertices[1].x<vertices[6].x);
    assert(vertices[1].u<vertices[6].u);

    FojGpuDrawRange draws[FOJ_RESEARCH_BATCH_COUNT];
    FojGpuDrawRange original_draws[FOJ_RESEARCH_BATCH_COUNT];
    memset(draws,0xA5,sizeof(draws));
    memcpy(original_draws,draws,sizeof(draws));
    assert(foj_gpu_build_draw_plan(batches,FOJ_RESEARCH_BATCH_COUNT,
             info.vertices_written,FOJ_RESEARCH_MATERIAL_COUNT,
             draws,FOJ_RESEARCH_BATCH_COUNT-1)==FOJ_GPU_STREAM_BOUNDS);
    assert(!memcmp(draws,original_draws,sizeof(draws)));
    assert(foj_gpu_build_draw_plan(NULL,FOJ_RESEARCH_BATCH_COUNT,
             info.vertices_written,FOJ_RESEARCH_MATERIAL_COUNT,
             draws,FOJ_RESEARCH_BATCH_COUNT)==FOJ_GPU_STREAM_ARGUMENT);
    assert(foj_gpu_build_draw_plan(batches,FOJ_RESEARCH_BATCH_COUNT,
             info.vertices_written,FOJ_RESEARCH_MATERIAL_COUNT,
             NULL,FOJ_RESEARCH_BATCH_COUNT)==FOJ_GPU_STREAM_ARGUMENT);

    /* A faulty second section must not leak the already-valid first draw. */
    FojGpuBatch bad[FOJ_RESEARCH_BATCH_COUNT];
    memcpy(bad,batches,sizeof(bad));
    bad[1].first_vertex=5;
    assert(foj_gpu_build_draw_plan(bad,FOJ_RESEARCH_BATCH_COUNT,
             info.vertices_written,FOJ_RESEARCH_MATERIAL_COUNT,
             draws,FOJ_RESEARCH_BATCH_COUNT)==FOJ_GPU_STREAM_INVALID);
    assert(!memcmp(draws,original_draws,sizeof(draws)));
    bad[1]=batches[1];
    bad[1].texture_index=FOJ_RESEARCH_MATERIAL_COUNT;
    assert(foj_gpu_build_draw_plan(bad,FOJ_RESEARCH_BATCH_COUNT,
             info.vertices_written,FOJ_RESEARCH_MATERIAL_COUNT,
             draws,FOJ_RESEARCH_BATCH_COUNT)==FOJ_GPU_STREAM_INVALID);
    assert(!memcmp(draws,original_draws,sizeof(draws)));
    bad[1]=batches[1];
    bad[1].vertex_count=3;
    assert(foj_gpu_build_draw_plan(bad,FOJ_RESEARCH_BATCH_COUNT,
             info.vertices_written,FOJ_RESEARCH_MATERIAL_COUNT,
             draws,FOJ_RESEARCH_BATCH_COUNT)==FOJ_GPU_STREAM_INVALID);
    assert(!memcmp(draws,original_draws,sizeof(draws)));
    bad[1].vertex_count=UINT32_MAX;
    assert(foj_gpu_build_draw_plan(bad,FOJ_RESEARCH_BATCH_COUNT,
             info.vertices_written,FOJ_RESEARCH_MATERIAL_COUNT,
             draws,FOJ_RESEARCH_BATCH_COUNT)==FOJ_GPU_STREAM_INVALID);
    assert(!memcmp(draws,original_draws,sizeof(draws)));

    assert(foj_gpu_build_draw_plan(batches,FOJ_RESEARCH_BATCH_COUNT,
             info.vertices_written,FOJ_RESEARCH_MATERIAL_COUNT,
             draws,FOJ_RESEARCH_BATCH_COUNT)==FOJ_GPU_STREAM_OK);
    assert(draws[0].first_vertex==0 && draws[0].vertex_count==6);
    assert(draws[1].first_vertex==6 && draws[1].vertex_count==6);
    assert(draws[0].material_index==0 && draws[1].material_index==1);
    puts("GPU ordered two-batch synthetic research mesh: PASS");
    return 0;
}
