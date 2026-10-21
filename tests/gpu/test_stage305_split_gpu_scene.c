/* Stage305 host-only test of exact C geometry and both BC1 pages.
 * Never claim GPU render without separate actual NeXium screenshots. */
#include "stage305_split_gpu_scene.h"
#include <assert.h>
#include <stdint.h>
#include <stdlib.h>
#include <stdio.h>
#include <string.h>

static const unsigned char known[3][4]={
    {96,72,201,128},{232,55,28,128},{21,202,219,255}
};
static void fixture(FojGpuPrivateBundleData *bundle) {
    memset(bundle,0,sizeof(*bundle));
    bundle->report.atlas_count=3;
    bundle->report.actor.stream.vertices_written=9u;
    bundle->report.actor.stream.batches_written=3u;
    bundle->vertices=(FojGpuVertex*)calloc(9u,sizeof(FojGpuVertex));
    bundle->batches=(FojGpuBatch*)calloc(3u,sizeof(FojGpuBatch));
    assert(bundle->vertices && bundle->batches);
    for(unsigned i=0;i<3u;++i) {
        bundle->batches[i]=(FojGpuBatch){3u*i,3u,i};
        bundle->rgba[i]=(unsigned char*)malloc(64u*64u*4u);
        assert(bundle->rgba[i]);
        bundle->report.atlas[i]=(FojAtlasRgba8Info){64u,64u,64u*64u*4u};
        for(size_t p=0;p<64u*64u*4u;p+=4u)
            memcpy(bundle->rgba[i]+p,known[i],4u);
    }
}
static void release(FojGpuPrivateBundleData *bundle) {
    for(unsigned i=0;i<3u;++i)free(bundle->rgba[i]);
    free(bundle->vertices);free(bundle->batches);
}
static void validate_pixels(const uint8_t *pixels,const uint8_t[4]) ;
static void validate_pixels(const uint8_t *pixels,const uint8_t expected[4]) {
    assert(pixels!=NULL);
    for(size_t p=0;p<256u*256u*4u;p+=4u)
        assert(memcmp(pixels+p,expected,4u)==0);
}
static void positive(void) {
    FojGpuPrivateBundleData b;fixture(&b);
    uint8_t *original0=b.rgba[0];
    assert(foj_stage305_apply_split_surface(&b)==1);
    assert(b.rgba[0]==original0);
    assert(b.report.actor.stream.vertices_written==15u);
    assert(b.report.actor.stream.batches_written==3u);
    const FojGpuBatch expected_batches[3]={
        {0u,3u,0u},{3u,6u,1u},{9u,6u,2u}
    };
    for(unsigned i=0;i<3u;++i)
        assert(memcmp(&b.batches[i],&expected_batches[i],
                      sizeof(FojGpuBatch))==0);
    const uint8_t l[4]={16,199,214,255},r[4]={24,203,222,255};
    validate_pixels(b.rgba[1],r);
    validate_pixels(b.rgba[2],l);
    for(unsigned i=1;i<=2;++i)
        assert(b.report.atlas[i].width==256u &&
               b.report.atlas[i].height==256u &&
               b.report.atlas[i].pixel_bytes==256u*256u*4u);
    /* Right geometry occupies [0,+0.6], left occupies [-0.6,0],
     * each with two triangles. Both use identical vertical bounds. */
    for(unsigned i=3;i<9u;++i) {
        const FojGpuVertex *v=&b.vertices[i];
        assert(v->x>=0.f && v->x<=.6f &&
               v->y>=-.5f && v->y<=.5f);
        assert(v->u==.5f && v->v==.5f && v->w==1.f);
    }
    for(unsigned i=9;i<15u;++i) {
        const FojGpuVertex *v=&b.vertices[i];
        assert(v->x>=-.6f && v->x<=0.f &&
               v->y>=-.5f && v->y<=.5f);
        assert(v->u==.5f && v->v==.5f && v->w==1.f);
    }
    assert(b.vertices[3].x==0.f && b.vertices[9].x==-.6f);
    assert(foj_stage305_apply_split_surface(&b)==0);
    release(&b);
}
static void negative(void) {
    assert(foj_stage305_apply_split_surface(NULL)==0);
    for (unsigned slot=0;slot<3u;++slot) {
        FojGpuPrivateBundleData b;fixture(&b);
        uint8_t *previous=b.rgba[2];
        FojGpuVertex *vertices=b.vertices;
        b.rgba[slot][10u]^=1u;
        assert(foj_stage305_apply_split_surface(&b)==0);
        assert(b.rgba[2]==previous && b.vertices==vertices);
        release(&b);
    }
    for (unsigned slot=0;slot<3u;++slot) {
        FojGpuPrivateBundleData b;fixture(&b);
        b.batches[slot].vertex_count=2u;
        assert(foj_stage305_apply_split_surface(&b)==0);
        assert(b.report.actor.stream.vertices_written==9u);
        release(&b);
    }
    {
        FojGpuPrivateBundleData b;fixture(&b);
        b.report.atlas[2].height=16u;
        assert(foj_stage305_apply_split_surface(&b)==0);
        release(&b);
    }
}
int main(void) {
    positive();negative();
    puts("STAGE305_NATIVE_TWO_PAGE_SPLIT_QUAD_CPU_PASS");
    return 0;
}
