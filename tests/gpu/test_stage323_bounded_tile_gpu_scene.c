/* Stage323: native scene test. A host model cannot prove GPU rendering. */
#include "stage309_seam_gutter_scene.h"
#include "stage314_four_page_corner.h"
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
enum { INPUT_SIZE=64*64*4, OUTPUT_SIZE=FOJ_BC1_PAGE_RGBA_BYTES };
static const uint8_t source_colors[3][4]={
    {96,72,201,128},{232,55,28,128},{21,202,219,255}
};
static const uint8_t four_colors[4][4]={
    {255,0,0,255},{0,255,0,255},{0,0,255,255},{255,255,255,255}
};
static void init(FojGpuPrivateBundleData *b) {
    memset(b,0,sizeof(*b));
    b->report.atlas_count=3u;
    b->report.actor.stream.vertices_written=9u;
    b->report.actor.stream.batches_written=3u;
    b->vertices=(FojGpuVertex*)calloc(9u,sizeof(FojGpuVertex));
    b->batches=(FojGpuBatch*)calloc(3u,sizeof(FojGpuBatch));
    assert(b->vertices && b->batches);
    for(unsigned i=0;i<3u;++i) {
        b->rgba[i]=(uint8_t*)malloc(INPUT_SIZE);
        assert(b->rgba[i]);
        for(size_t k=0;k<INPUT_SIZE;k+=4u)
            memcpy(b->rgba[i]+k,source_colors[i],4u);
        b->report.atlas[i]=(FojAtlasRgba8Info){64u,64u,INPUT_SIZE};
        b->batches[i]=(FojGpuBatch){i*3u,3u,i};
    }
}
static void done(FojGpuPrivateBundleData *b) {
    for(unsigned i=0;i<3u;++i)free(b->rgba[i]);
    free(b->vertices);free(b->batches);
}
static void happy(void) {
    FojGpuPrivateBundleData b;init(&b);
    assert(foj_stage309_prepare_gutter_scene(&b)==1);
    assert(b.report.actor.stream.vertices_written==18u);
    assert(b.report.actor.stream.batches_written==3u);
    for(unsigned i=0;i<3u;++i) {
        const unsigned edge=i==0u?16u:256u;
        const unsigned bytes=i==0u?16u*16u*4u:OUTPUT_SIZE;
        assert(b.report.atlas[i].width==edge);
        assert(b.report.atlas[i].height==edge);
        assert(b.report.atlas[i].pixel_bytes==bytes);
        assert(b.batches[i].first_vertex==i*6u);
        assert(b.batches[i].vertex_count==6u);
        assert(b.batches[i].texture_index==i);
    }
    for(unsigned y=0;y<16u;++y)for(unsigned x=0;x<16u;++x) {
        const unsigned which=(y>=8u?2u:0u)+(x>=8u?1u:0u);
        assert(memcmp(b.rgba[0]+((size_t)y*16u+x)*4u,
                      four_colors[which],4u)==0);
    }
    for(unsigned y=0;y<256u;++y)for(unsigned x=0;x<256u;++x) {
        assert(memcmp(b.rgba[1]+((size_t)y*256u+x)*4u,
                      four_colors[3],4u)==0);
        assert(memcmp(b.rgba[2]+((size_t)y*256u+x)*4u,
                      four_colors[0],4u)==0);
    }
    const float lo=7.5f/16.f,hi=8.5f/16.f;
    assert(b.vertices[0].u==lo && b.vertices[0].v==hi);
    assert(b.vertices[1].u==hi && b.vertices[1].v==hi);
    assert(b.vertices[2].u==lo && b.vertices[2].v==lo);
    assert(b.vertices[0].x==-.52f && b.vertices[1].x==.52f);
    assert(b.vertices[0].y==-.48f && b.vertices[2].y==.48f);
    for(unsigned i=0;i<6u;++i)assert(b.vertices[i].z==.68f);
    for(unsigned i=6u;i<18u;++i)assert(b.vertices[i].z==.55f);
    assert(b.vertices[0].z>b.vertices[6].z);
    assert(b.vertices[0].z>b.vertices[12].z);
    assert(foj_stage309_prepare_gutter_scene(&b)==0);
    done(&b);
}
static void refuse(void) {
    assert(!foj_stage309_prepare_gutter_scene(NULL));
    for(unsigned i=0;i<3u;++i) {
        FojGpuPrivateBundleData b;init(&b);
        uint8_t *saved=b.rgba[i];
        FojGpuVertex *original_vertices=b.vertices;
        b.rgba[i][12]^=1u;
        assert(!foj_stage309_prepare_gutter_scene(&b));
        assert(b.rgba[i]==saved && b.vertices==original_vertices);
        done(&b);
    }
    for(unsigned i=0;i<3u;++i) {
        FojGpuPrivateBundleData b;init(&b);
        b.batches[i].vertex_count=4u;
        assert(!foj_stage309_prepare_gutter_scene(&b));
        assert(b.report.actor.stream.vertices_written==9u);
        done(&b);
    }
}
int main(void) {
    happy();refuse();
    puts("STAGE323_NATIVE_BOUNDED_1024_BYTE_TILE_GPU_SCENE_PASS");
    return 0;
}
