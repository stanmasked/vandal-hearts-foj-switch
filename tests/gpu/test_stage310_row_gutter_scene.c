/* Stage310 opt-in NRO mode: host executes the exact GPU-side stage309
 * 18-vertex builder configured for EIGHT actual decoded BC1 row bands.
 * No original PS3 asset can enter these in-memory synthetic fixtures.
 */
#include "stage309_seam_gutter_scene.h"
#include "stage308_cross_page_bilinear.h"
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static const uint8_t known[3][4]={
    {96,72,201,128},{232,55,28,128},{21,202,219,255}
};
static const uint16_t bands[2][8]={
    {0x001fu,0xf800u,0x07e0u,0xffe0u,0xf81fu,0x07ffu,0xffffu,0x0000u},
    {0xffe0u,0x07e0u,0x001fu,0xf800u,0x07ffu,0xf81fu,0x0000u,0xffffu}
};
static void rgb565(uint16_t v,uint8_t out[4]) {
    unsigned r=(v>>11u)&31u,g=(v>>5u)&63u,b=v&31u;
    out[0]=(uint8_t)((r<<3u)|(r>>2u));
    out[1]=(uint8_t)((g<<2u)|(g>>4u));
    out[2]=(uint8_t)((b<<3u)|(b>>2u));
    out[3]=255u;
}
static void setup(FojGpuPrivateBundleData *b) {
    memset(b,0,sizeof(*b));
    b->report.atlas_count=3u;
    b->report.actor.stream.vertices_written=9u;
    b->report.actor.stream.batches_written=3u;
    b->vertices=(FojGpuVertex*)calloc(9u,sizeof(FojGpuVertex));
    b->batches=(FojGpuBatch*)calloc(3u,sizeof(FojGpuBatch));
    assert(b->vertices && b->batches);
    for(unsigned i=0;i<3u;++i) {
        b->rgba[i]=(uint8_t*)malloc(64u*64u*4u);
        assert(b->rgba[i]);
        for(size_t n=0;n<64u*64u*4u;n+=4u)
            memcpy(b->rgba[i]+n,known[i],4u);
        b->report.atlas[i]=(FojAtlasRgba8Info){64u,64u,64u*64u*4u};
        b->batches[i]=(FojGpuBatch){i*3u,3u,i};
    }
}
static void teardown(FojGpuPrivateBundleData *b) {
    for(unsigned i=0;i<3u;++i)free(b->rgba[i]);
    free(b->vertices);free(b->batches);
}
static void positive(void) {
    FojGpuPrivateBundleData b;setup(&b);
    assert(foj_stage309_prepare_gutter_scene(&b)==1);
    assert(b.report.actor.stream.vertices_written==18u);
    assert(b.report.actor.stream.batches_written==3u);
    for(unsigned i=0;i<3u;++i) {
        assert(b.batches[i].first_vertex==i*6u);
        assert(b.batches[i].vertex_count==6u);
        assert(b.batches[i].texture_index==i);
        assert(b.report.atlas[i].width==256u);
        assert(b.report.atlas[i].height==256u);
        assert(b.report.atlas[i].pixel_bytes==FOJ_BC1_PAGE_RGBA_BYTES);
    }
    for(unsigned y=0;y<256u;++y) {
        uint8_t left[4],right[4],blended[4];
        rgb565(bands[0][y/32u],left);
        rgb565(bands[1][y/32u],right);
        for(unsigned x=0;x<256u;++x) {
            size_t idx=((size_t)y*256u+x)*4u;
            assert(memcmp(b.rgba[2]+idx,left,4u)==0);
            assert(memcmp(b.rgba[1]+idx,right,4u)==0);
            assert(memcmp(b.rgba[0]+idx,x<128u?left:right,4u)==0);
        }
        assert(foj_stage308_cross_page_bilinear(
            b.rgba[2],FOJ_BC1_PAGE_RGBA_BYTES,
            b.rgba[1],FOJ_BC1_PAGE_RGBA_BYTES,y,.5f,blended));
        assert(foj_stage308_requires_two_pages(left,right,blended));
    }
    for(unsigned i=0;i<6u;++i) {
        assert(b.vertices[i].z==.68f);
        assert(b.vertices[i].x>=-.03f && b.vertices[i].x<=.03f);
    }
    assert(b.vertices[0].z>b.vertices[6].z);
    assert(b.vertices[0].z>b.vertices[12].z);
    assert(b.vertices[0].u==127.5f/256.f);
    assert(b.vertices[1].u==128.5f/256.f);
    assert(b.vertices[6].x==0.f && b.vertices[12].x==-.6f);
    assert(b.vertices[7].x==.6f && b.vertices[13].x==0.f);
    uint8_t *const no_second_apply=b.rgba[0];
    assert(foj_stage309_prepare_gutter_scene(&b)==0);
    assert(b.rgba[0]==no_second_apply);
    teardown(&b);
}
static void negative(void) {
    assert(foj_stage309_prepare_gutter_scene(NULL)==0);
    for(unsigned slot=0;slot<3u;++slot) {
        FojGpuPrivateBundleData b;setup(&b);
        uint8_t *const old=b.rgba[0];
        FojGpuVertex *const old_verts=b.vertices;
        b.rgba[slot][17u]^=1u;
        assert(foj_stage309_prepare_gutter_scene(&b)==0);
        assert(b.rgba[0]==old && b.vertices==old_verts);
        teardown(&b);
    }
}
int main(void) {
    positive();negative();
    puts("STAGE310_REAL_C_GPU_SCENE_EIGHT_PATTERNED_ROW_BANDS_PASS");
    return 0;
}
