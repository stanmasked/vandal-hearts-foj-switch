/* Stage309 actual generated-only C scene and cross-page filter reference.
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
        assert(b.batches[i].material_index==i);
        assert(b.batches[i].first_vertex==i*6u);
        assert(b.batches[i].vertex_count==6u);
    }
    const uint8_t blue[4]={0,0,255,255};
    const uint8_t yellow[4]={255,255,0,255};
    const uint8_t midpoint_top[4]={128,128,128,255};
    const uint8_t red[4]={255,0,0,255};
    const uint8_t green[4]={0,255,0,255};
    const uint8_t midpoint_bottom[4]={128,128,0,255};
    for(unsigned y=0;y<256u;++y) {
        if(y<128u)check_half(y,&b,blue,yellow,midpoint_top);
        else check_half(y,&b,red,green,midpoint_bottom);
    }
    /* Gutter strip covers [-.03,+.03] and is closer in depth
     * than the two original pages at z=.55. Its U interpolates
     * between the exact two source texel centers around 0.5. */
    for(unsigned i=0;i<6u;++i)
        assert(b.vertices[i].z==.42f &&
               b.vertices[i].x>=-.03f && b.vertices[i].x<=.03f);
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
    puts("STAGE309_NATIVE_GENERATED_TWO_PAGE_GUTTER_AND_BLEND_REFERENCE_PASS");
    return 0;
}
