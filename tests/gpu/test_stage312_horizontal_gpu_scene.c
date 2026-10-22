/* Stage312: actual native generated-only 18-vertex horizontal GPU scene.
 * This host C check cannot replace independent live NeXium screenshots.
 */
#include "stage309_seam_gutter_scene.h"
#include "stage311_horizontal_gutter.h"
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static const uint8_t original[3][4]={
    {96,72,201,128},{232,55,28,128},{21,202,219,255}
};
static const uint16_t band565[2][8]={
    {0x001fu,0xf800u,0x07e0u,0xffe0u,0xf81fu,0x07ffu,0xffffu,0x0000u},
    {0xffe0u,0x07e0u,0x001fu,0xf800u,0x07ffu,0xf81fu,0x0000u,0xffffu}
};
static void rgba565(uint16_t v,uint8_t out[4]) {
    const unsigned r=(v>>11u)&31u,g=(v>>5u)&63u,b=v&31u;
    out[0]=(uint8_t)((r<<3u)|(r>>2u));
    out[1]=(uint8_t)((g<<2u)|(g>>4u));
    out[2]=(uint8_t)((b<<3u)|(b>>2u));
    out[3]=255u;
}
static void prepare(FojGpuPrivateBundleData *b) {
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
        for(size_t k=0;k<64u*64u*4u;k+=4u)
            memcpy(b->rgba[i]+k,original[i],4u);
        b->report.atlas[i]=(FojAtlasRgba8Info){64u,64u,64u*64u*4u};
        b->batches[i]=(FojGpuBatch){3u*i,3u,i};
    }
}
static void cleanup(FojGpuPrivateBundleData *b) {
    for(unsigned i=0;i<3u;++i)free(b->rgba[i]);
    free(b->vertices);free(b->batches);
}
static void happy(void) {
    FojGpuPrivateBundleData b;prepare(&b);
    assert(foj_stage309_prepare_gutter_scene(&b)==1);
    assert(b.report.actor.stream.vertices_written==18u);
    assert(b.report.actor.stream.batches_written==3u);
    for(unsigned i=0;i<3u;++i) {
        assert(b.report.atlas[i].width==256u);
        assert(b.report.atlas[i].height==256u);
        assert(b.report.atlas[i].pixel_bytes==FOJ_BC1_PAGE_RGBA_BYTES);
        assert(b.batches[i].first_vertex==i*6u);
        assert(b.batches[i].vertex_count==6u);
        assert(b.batches[i].texture_index==i);
    }
    for(unsigned x=0;x<256u;++x) {
        const unsigned band=x/32u;
        uint8_t up[4],down[4],mid[4]={0};
        rgba565(band565[0][band],up);
        rgba565(band565[1][band],down);
        assert(foj_stage311_horizontal_bilinear(
            b.rgba[2],FOJ_BC1_PAGE_RGBA_BYTES,
            b.rgba[1],FOJ_BC1_PAGE_RGBA_BYTES,x,.5f,mid));
        for(unsigned k=0;k<4u;++k)
            assert(mid[k]==(uint8_t)((up[k]+down[k]+1u)/2u));
        for(unsigned y=0;y<256u;++y) {
            const size_t offset=((size_t)y*256u+x)*4u;
            const uint8_t *expect=y<128u?up:down;
            assert(memcmp(b.rgba[0]+offset,expect,4u)==0);
            assert(memcmp(b.rgba[2]+offset,up,4u)==0);
            assert(memcmp(b.rgba[1]+offset,down,4u)==0);
        }
    }
    /* At reverse-Z Greater, closer overlay has GREATER depth value;
     * horizontal gutter patch occupies screen Y=-.03..+.03. */
    for(unsigned i=0;i<6u;++i) {
        assert(b.vertices[i].z==.68f);
        assert(b.vertices[i].y>=-.03f && b.vertices[i].y<=.03f);
        assert(b.vertices[i].x>=-.6f && b.vertices[i].x<=.6f);
    }
    assert(b.vertices[0].z>b.vertices[6].z);
    assert(b.vertices[0].z>b.vertices[12].z);
    assert(b.vertices[6].z==.55f && b.vertices[12].z==.55f);
    assert(b.vertices[0].v==128.5f/256.f);
    assert(b.vertices[2].v==127.5f/256.f);
    assert(b.vertices[6].y==-.5f && b.vertices[8].y==0.f);
    assert(b.vertices[12].y==0.f && b.vertices[14].y==.5f);
    assert(b.vertices[0].u==0.f && b.vertices[1].u==1.f);
    uint8_t *original_bridge=b.rgba[0];
    assert(foj_stage309_prepare_gutter_scene(&b)==0);
    assert(b.rgba[0]==original_bridge);
    cleanup(&b);
}
static void refuse(void) {
    assert(foj_stage309_prepare_gutter_scene(NULL)==0);
    for(unsigned i=0;i<3u;++i) {
        FojGpuPrivateBundleData b;prepare(&b);
        FojGpuVertex *old_vertices=b.vertices;
        uint8_t *old_rgba=b.rgba[0];
        b.rgba[i][19u]^=1u;
        assert(foj_stage309_prepare_gutter_scene(&b)==0);
        assert(b.vertices==old_vertices && b.rgba[0]==old_rgba);
        cleanup(&b);
    }
    for(unsigned i=0;i<3u;++i) {
        FojGpuPrivateBundleData b;prepare(&b);
        b.batches[i].vertex_count=4u;
        assert(foj_stage309_prepare_gutter_scene(&b)==0);
        assert(b.report.actor.stream.vertices_written==9u);
        cleanup(&b);
    }
}
int main(void) {
    happy();refuse();
    puts("STAGE312_NATIVE_HORIZONTAL_BC1_SCENE_18_VERTICES_8_BANDS_PASS");
    return 0;
}
