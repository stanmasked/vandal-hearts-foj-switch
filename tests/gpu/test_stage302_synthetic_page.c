/* Host-only Stage302 regression: tests the *actual* C function called by
 * NeXium research NRO; no private/PS3 images or emulator claims. */
#include "stage302_synthetic_page_probe.h"
#include <assert.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <stdio.h>

static const uint8_t original[3][4]={
    {96,72,201,128}, {232,55,28,128}, {21,202,219,255}
};
static void fixture(FojGpuPrivateBundleData *b) {
    memset(b,0,sizeof(*b));
    b->report.atlas_count=3;
    for (unsigned i=0;i<3;++i) {
        b->rgba[i]=malloc(64u*64u*4u);
        assert(b->rgba[i]);
        for (unsigned j=0;j<64u*64u;++j)
            memcpy(b->rgba[i]+4u*j,original[i],4u);
        b->report.atlas[i]=(FojAtlasRgba8Info){64u,64u,64u*64u*4u};
    }
}
static void cleanup(FojGpuPrivateBundleData *b) {
    for (unsigned i=0;i<3;++i)free(b->rgba[i]);
}
static void check_output(void) {
    FojGpuPrivateBundleData b;fixture(&b);
    uint8_t *const a=b.rgba[0],*const m=b.rgba[1];
    assert(foj_stage302_apply_generated_page(&b)==1);
    assert(b.report.atlas[2].width==256u);
    assert(b.report.atlas[2].height==256u);
    assert(b.report.atlas[2].pixel_bytes==256u*256u*4u);
    assert(b.rgba[0]==a && b.rgba[1]==m);
    const uint8_t color[4]={24,203,222,255};
    for (size_t p=0;p<256u*256u;++p)
        assert(memcmp(b.rgba[2]+4u*p,color,4u)==0);
    /* A now-nonmatching rear prevents running this experimental mode twice. */
    assert(foj_stage302_apply_generated_page(&b)==0);
    cleanup(&b);
}
static void check_wrong_data(void) {
    for (unsigned slot=0;slot<3;++slot) {
        FojGpuPrivateBundleData b;fixture(&b);
        uint8_t *const old=b.rgba[2];
        b.rgba[slot][17] ^= 1u;
        assert(foj_stage302_apply_generated_page(&b)==0);
        assert(b.rgba[2]==old && b.report.atlas[2].width==64u);
        cleanup(&b);
    }
}
static void check_wrong_metadata(void) {
    for (unsigned slot=0;slot<3;++slot) {
        FojGpuPrivateBundleData b;fixture(&b);
        b.report.atlas[slot].width=16u;
        assert(foj_stage302_apply_generated_page(&b)==0);
        assert(b.report.atlas[2].height==64u);
        cleanup(&b);
    }
}
static void check_invalid_null_missing(void) {
    assert(foj_stage302_apply_generated_page(NULL)==0);
    for (unsigned slot=0;slot<3;++slot) {
        FojGpuPrivateBundleData b;fixture(&b);
        free(b.rgba[slot]);b.rgba[slot]=NULL;
        assert(foj_stage302_apply_generated_page(&b)==0);
        cleanup(&b);
    }
}
int main(void) {
    check_output();
    check_wrong_data();
    check_wrong_metadata();
    check_invalid_null_missing();
    puts("STAGE302_NATIVE_GENERATED_BC1_1024_GUEST_INPUT_PARITY_PASS");
    return 0;
}
