/* Stage310 actual generated-only C scene and cross-page filter reference.
 * Any real GPU proof must additionally come from NeXium live captures.
 */
#include "stage309_seam_gutter_scene.h"
#include "stage308_cross_page_bilinear.h"
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static const uint8_t original[3][4]={
    {96,72,201,128},{232,55,28,128},{21,202,219,255}
};
static void prepare(FojGpuPrivateBundleData *b) {
    memset(b,0,sizeof(*b));
    b->report.atlas_count=3u;
    b->report.actor.stream.vertices_written=9u;
    b->report.actor.stream.batches_written=3u;
    b->vertices=(FojGpuVertex*)calloc(9u,sizeof(FojGpuVertex));
    b->batches=(FojGpuBatch*)calloc(3u,sizeof(FojGpuBatch));
    assert(b->vertices && b->batches);
    for (unsigned i=0;i<3u;++i) {
        b->rgba[i]=(uint8_t*)malloc(64u*64u*4u);
        assert(b->rgba[i]);
        for (size_t p=0;p<64u*64u*4u;p+=4u)
            memcpy(b->rgba[i]+p,original[i],4u);
        b->report.atlas[i]=(FojAtlasRgba8Info){64u,64u,64u*64u*4u};
        b->batches[i]=(FojGpuBatch){3u*i,3u,i};
    }
}
static void cleanup(FojGpuPrivateBundleData *b) {
    for(unsigned i=0;i<3u;++i)free(b->rgba[i]);
    free(b->vertices);free(b->batches);
}
static const uint16_t bands[2][8]={
    {0x001fu,0xf800u,0x07e0u,0xffe0u,0xf81fu,0x07ffu,0xffffu,0x0000u},
    {0xffe0u,0x07e0u,0x001fu,0xf800u,0x07ffu,0xf81fu,0x0000u,0xffffu}
};
static void rgb565(uint16_t v,uint8_t p[4]) {
    unsigned r=(v>>11u)&31u,g=(v>>5u)&63u,b=v&31u;
    p[0]=(uint8_t)((r<<3u)|(r>>2u));
    p[1]=(uint8_t)((g<<2u)|(g>>4u));
    p[2]=(uint8_t)((b<<3u)|(b>>2u));
    p[3]=255u;
}
static void check_half(unsigned y,const FojGpuPrivateBundleData *b,
                       const uint8_t l[4],const uint8_t r[4],
                       const uint8_t midpoint[4]) {
    const size_t row=(size_t)y*256u*4u;
    for(unsigned x=0;x<256u;++x) {
        assert(memcmp(b->rgba[2]+row+4u*x,l,4u)==0);
        assert(memcmp(b->rgba[1]+row+4u*x,r,4u)==0);
        const uint8_t *expected=(x<128u)?l:r;
        assert(memcmp(b->rgba[0]+row+4u*x,expected,4u)==0);
    }
    uint8_t actual[4]={0};
    assert(foj_stage308_cross_page_bilinear(
        b->rgba[2],FOJ_BC1_PAGE_RGBA_BYTES,
        b->rgba[1],FOJ_BC1_PAGE_RGBA_BYTES,y,.5f,actual)==1);
    assert(memcmp(actual,midpoint,4u)==0);
    assert(foj_stage308_requires_two_pages(l,r,midpoint)==1);
}
static void positive(void) {
    FojGpuPrivateBundleData b;prepare(&b);
    assert(foj_stage309_prepare_gutter_scene(&b)==1);
    assert(b.report.actor.stream.vertices_written==18u);
    assert(b.report.actor.stream.batches_written==3u);
    for(unsigned i=0;i<3u;++i) {
        assert(b.report.atlas[i].width==256u &&
               b.report.atlas[i].height==256u &&
               b.report.atlas[i].pixel_bytes==FOJ_BC1_PAGE_RGBA_BYTES);
        assert(b.batches[i].texture_index==i);
        assert(b.batches[i].first_vertex==i*6u);
        assert(b.batches[i].vertex_count==6u);
    }
    for(unsigned y=0;y<256u;++y) {
        uint8_t left[4],right[4],midpoint[4];
        rgb565(bands[0][y/32u],left);
        rgb565(bands[1][y/32u],right);
        for(unsigned channel=0;channel<4u;++channel)
            midpoint[channel]=(uint8_t)((left[channel]+
                                        right[channel]+1u)/2u);
        check_half(y,&b,left,right,midpoint);
    }
    /* Gutter strip covers [-.03,+.03] and is closer in depth
     * than the two original pages at z=.55. Its U interpolates
     * between the exact two source texel centers around 0.5. */
    for(unsigned i=0;i<6u;++i)
        assert(b.vertices[i].z==.68f &&
               b.vertices[i].x>=-.03f && b.vertices[i].x<=.03f);
    /* Renderer uses reverse-Z: clear 0.0, compare Greater. The final
     * overlay draw must be nearer (greater Z) than base two pages. */
    assert(b.vertices[0].z>b.vertices[6].z);
    assert(b.vertices[0].z>b.vertices[12].z);
    assert(b.vertices[6].z==.55f && b.vertices[12].z==.55f);
    assert(b.vertices[0].u==127.5f/256.f);
    assert(b.vertices[1].u==128.5f/256.f);
    assert(b.vertices[6].x==0.f && b.vertices[12].x==-.6f);
    assert(b.vertices[7].x==.6f && b.vertices[13].x==0.f);
    /* An already converted bundle must fail closed. */
    uint8_t *const bridge=b.rgba[0];
    assert(foj_stage309_prepare_gutter_scene(&b)==0);
    assert(b.rgba[0]==bridge);
    cleanup(&b);
}
static void negative(void) {
    assert(foj_stage309_prepare_gutter_scene(NULL)==0);
    for(unsigned slot=0;slot<3u;++slot) {
        FojGpuPrivateBundleData b;prepare(&b);
        FojGpuVertex *const verts=b.vertices;
        uint8_t *const old=b.rgba[0];
        b.rgba[slot][19u]^=1u;
        assert(foj_stage309_prepare_gutter_scene(&b)==0);
        assert(b.rgba[0]==old && b.vertices==verts);
        cleanup(&b);
    }
    for(unsigned slot=0;slot<3u;++slot) {
        FojGpuPrivateBundleData b;prepare(&b);
        b.batches[slot].vertex_count=4u;
        assert(foj_stage309_prepare_gutter_scene(&b)==0);
        assert(b.report.actor.stream.vertices_written==9u);
        cleanup(&b);
    }
}
int main(void) {
    positive();negative();
    puts("STAGE310_NATIVE_EIGHT_BAND_GUTTER_SCENE_AND_BLEND_PASS");
    return 0;
}
