/* Exact generated-only CPU preflight for the Stage329 native GPU scene. */
#include "stage328_atomic_corner_patch_stream.h"
#include "stage320_uv_page_batches.h"
#include <assert.h>
#include <math.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

static uint8_t page_data[4][FOJ_BC1_PAGE_RGBA_BYTES];
static uint8_t tile[FOJ_STAGE322_TILE_BYTES];
static FojTexturedVertex stream[FOJ_STAGE328_MAX_VERTICES];
static FojTextureSection sections[FOJ_STAGE328_MAX_SECTIONS];
static FojGpuVertex gpu_vertices[FOJ_STAGE328_MAX_VERTICES];
static FojGpuBatch gpu_batches[FOJ_STAGE328_MAX_SECTIONS];

static uint64_t fnv1a(const uint8_t *data,size_t size) {
    uint64_t hash=UINT64_C(14695981039346656037);
    for(size_t i=0u;i<size;++i) {
        hash^=data[i];
        hash*=UINT64_C(1099511628211);
    }
    return hash;
}
int main(void) {
    static const uint8_t colors[4][4]={
        {255u,0u,0u,255u},{0u,255u,0u,255u},
        {0u,0u,255u,255u},{255u,255u,255u,255u}
    };
    for(unsigned page=0u;page<4u;++page)
        for(size_t offset=0u;offset<FOJ_BC1_PAGE_RGBA_BYTES;offset+=4u)
            memcpy(page_data[page]+offset,colors[page],4u);
    const uint8_t *const pages[4]={
        page_data[0],page_data[1],page_data[2],page_data[3]
    };
    const size_t lengths[4]={
        FOJ_BC1_PAGE_RGBA_BYTES,FOJ_BC1_PAGE_RGBA_BYTES,
        FOJ_BC1_PAGE_RGBA_BYTES,FOJ_BC1_PAGE_RGBA_BYTES
    };

    const float u0=504.25f/1024.f,v0=504.25f/1024.f;
    const float u1=519.75f/1024.f,v1=504.25f/1024.f;
    const float u2=512.f/1024.f,v2=519.75f/1024.f;
    const FojStage318Triangle uv={{{u0,v0},{u1,v1},{u2,v2}}};
    FojStage325Triangle triangle={0};
    triangle.point[0]=(FojStage325Vertex){
        (u0-.5f)*200.f,(v0-.5f)*200.f,.5f,u0,v0};
    triangle.point[1]=(FojStage325Vertex){
        (u1-.5f)*200.f,(v1-.5f)*200.f,.5f,u1,v1};
    triangle.point[2]=(FojStage325Vertex){
        (u2-.5f)*200.f,(v2-.5f)*200.f,.5f,u2,v2};

    uint16_t ordered_ids[1]={0u};
    FojStage320Batch batches[1]={{0}};
    FojStage320Plan plan={0};
    assert(foj_stage320_plan_triangle_batches(
        &uv,1u,ordered_ids,1u,batches,1u,&plan));
    assert(plan.batch_count==1u&&ordered_ids[0]==0u);
    assert(batches[0].index_count==1u);
    const uint16_t expected_mask=(uint16_t)((1u<<5u)|(1u<<6u)|(1u<<9u)|(1u<<10u));
    assert(batches[0].filter_mask==expected_mask);

    FojStage328Receipt receipt={0};
    assert(foj_stage328_prepare_corner_patch_stream(
        batches,&triangle,1u,2u,2u,pages,lengths,0u,1u,2u,
        tile,sizeof(tile),stream,FOJ_STAGE328_MAX_VERTICES,
        sections,FOJ_STAGE328_MAX_SECTIONS,&receipt));
    assert(receipt.tile_fnv1a64==UINT64_C(0xd5565bfb7360b325));
    assert(fnv1a(tile,sizeof(tile))==receipt.tile_fnv1a64);
    assert(receipt.atlas_first_x==504u&&receipt.atlas_first_y==504u);
    assert(receipt.source_page_mask==expected_mask);
    assert(receipt.page_id[0]==5u&&receipt.page_id[1]==6u);
    assert(receipt.page_id[2]==9u&&receipt.page_id[3]==10u);
    assert(receipt.midpoint_rgba[0]==128u&&receipt.midpoint_rgba[1]==128u&&
           receipt.midpoint_rgba[2]==128u&&receipt.midpoint_rgba[3]==255u);
    assert(receipt.output_vertices==3u&&receipt.output_sections==1u);
    assert(receipt.tile_fragments==1u&&receipt.remainder_fragments==0u);
    assert(receipt.tile_texture_index==1u&&receipt.source_texture_index==0u);
    assert(sections[0].first_vertex==0u&&sections[0].vertex_count==3u&&
           sections[0].texture_index==1u);

    for(unsigned y=0u;y<16u;++y)for(unsigned x=0u;x<16u;++x) {
        const unsigned corner=(y>=8u?2u:0u)+(x>=8u?1u:0u);
        for(unsigned c=0u;c<4u;++c)
            assert(tile[((size_t)y*16u+x)*4u+c]==colors[corner][c]);
    }

    float min_u=1.f,max_u=0.f,min_v=1.f,max_v=0.f;
    for(size_t i=0u;i<receipt.output_vertices;++i) {
        /* Stage324/327 already emits tile-section UVs in local [0,1]. */
        assert(stream[i].u>=0.f&&stream[i].u<=1.f);
        assert(stream[i].v>=0.f&&stream[i].v<=1.f);
        if(stream[i].u<min_u)min_u=stream[i].u;
        if(stream[i].u>max_u)max_u=stream[i].u;
        if(stream[i].v<min_v)min_v=stream[i].v;
        if(stream[i].v>max_v)max_v=stream[i].v;
    }
    assert(min_u<.02f&&max_u>.98f&&min_v<.02f&&max_v>.98f);
    const FojTextureCamera camera={0.f,0.f,0.f,9.5f,0.f,0.f,1.f,1};
    FojGpuStreamInfo info={0};
    assert(foj_gpu_prepare_stream(
        stream,receipt.output_vertices,sections,receipt.output_sections,2u,
        &camera,1280u,720u,gpu_vertices,FOJ_STAGE328_MAX_VERTICES,
        gpu_batches,FOJ_STAGE328_MAX_SECTIONS,&info)==FOJ_GPU_STREAM_OK);
    assert(info.vertices_written==3u&&info.batches_written==1u);
    assert(gpu_batches[0].texture_index==1u);
    for(unsigned i=0u;i<3u;++i) {
        assert(isfinite(gpu_vertices[i].x)&&isfinite(gpu_vertices[i].y));
        assert(fabsf(gpu_vertices[i].v-(1.f-stream[i].v))<1e-6f);
        assert(fabsf(gpu_vertices[i].z-.5f)<1e-6f);
    }
    puts("STAGE329_GENERATED_CORNER_PATCH_CPU_PASS");
    return 0;
}
