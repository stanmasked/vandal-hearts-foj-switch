/* Stage304 native CPU witness for both adjacent pages and strict unchanged
 * failure state. Invented data only; a separate NeXium run proves GPU. */
#include "stage304_uv_seam_probe.h"
#include <assert.h>
#include <stdlib.h>
#include <stdio.h>
#include <stdint.h>
#include <string.h>

static const uint8_t colors[3][4]={
    {96,72,201,128},{232,55,28,128},{21,202,219,255}
};
static void init(FojGpuPrivateBundleData *b) {
    memset(b,0,sizeof(*b));
    b->report.atlas_count=3u;
    for(unsigned slot=0;slot<3u;++slot) {
        b->rgba[slot]=(uint8_t*)malloc(64u*64u*4u);
        assert(b->rgba[slot]);
        for(unsigned i=0;i<64u*64u;++i)
            memcpy(b->rgba[slot]+4u*i,colors[slot],4u);
        b->report.atlas[slot]=(FojAtlasRgba8Info){64u,64u,64u*64u*4u};
    }
}
static void release(FojGpuPrivateBundleData *b) {
    for(unsigned i=0;i<3u;++i)free(b->rgba[i]);
}
static void positive(unsigned side) {
    FojGpuPrivateBundleData b;init(&b);
    const uint8_t *first=b.rgba[0],*middle=b.rgba[1];
    FojBc1PageUv uv={0};
    assert(foj_stage304_apply_seam_probe(&b,side,&uv)==1);
    assert(uv.page_x==1u+side && uv.page_y==1u);
    assert(uv.atlas_x==(side==0?511u:512u));
    assert(uv.atlas_y==384u);
    assert(uv.local_x==(side==0?255u:0u));
    assert(uv.local_y==128u);
    assert(b.report.atlas[2].width==256u);
    assert(b.report.atlas[2].height==256u);
    assert(b.report.atlas[2].pixel_bytes==256u*256u*4u);
    assert(b.rgba[0]==first && b.rgba[1]==middle);
    const uint8_t expected[4]={
        (uint8_t)(side==0?16u:24u),
        (uint8_t)(side==0?199u:203u),
        (uint8_t)(side==0?214u:222u),255u
    };
    for(size_t i=0;i<256u*256u*4u;i+=4u)
        assert(memcmp(b.rgba[2]+i,expected,4u)==0);
    /* Already transformed input must never be accepted again. */
    assert(foj_stage304_apply_seam_probe(&b,side,&uv)==0);
    release(&b);
}
static void negatives(void) {
    FojBc1PageUv uv={3,4,5,6,7,8,0.25f,0.75f};
    const FojBc1PageUv before=uv;
    assert(foj_stage304_apply_seam_probe(NULL,0,&uv)==0);
    assert(memcmp(&uv,&before,sizeof(uv))==0);
    for(unsigned bad=2;bad<8;++bad) {
        FojGpuPrivateBundleData b;init(&b);
        uint8_t *const rear=b.rgba[2];
        assert(foj_stage304_apply_seam_probe(&b,bad,&uv)==0);
        assert(b.rgba[2]==rear && b.report.atlas[2].width==64u);
        assert(memcmp(&uv,&before,sizeof(uv))==0);
        release(&b);
    }
    for(unsigned slot=0;slot<3u;++slot) {
        FojGpuPrivateBundleData b;init(&b);
        uint8_t *const rear=b.rgba[2];
        b.rgba[slot][17u]^=1u;
        assert(foj_stage304_apply_seam_probe(&b,0,&uv)==0);
        assert(b.rgba[2]==rear && b.report.atlas[2].height==64u);
        assert(memcmp(&uv,&before,sizeof(uv))==0);
        release(&b);
    }
    for(unsigned slot=0;slot<3u;++slot) {
        FojGpuPrivateBundleData b;init(&b);
        uint8_t *const rear=b.rgba[2];
        b.report.atlas[slot].height=32u;
        assert(foj_stage304_apply_seam_probe(&b,1,&uv)==0);
        assert(b.rgba[2]==rear && b.report.atlas[2].width==64u);
        release(&b);
    }
    FojGpuPrivateBundleData b;init(&b);
    assert(foj_stage304_apply_seam_probe(&b,0,NULL)==0);
    release(&b);
}
int main(void) {
    positive(FOJ_STAGE304_LEFT);
    positive(FOJ_STAGE304_RIGHT);
    negatives();
    puts("STAGE304_NATIVE_BC1_UV_NEIGHBOR_PAGES_PASS");
    return 0;
}
