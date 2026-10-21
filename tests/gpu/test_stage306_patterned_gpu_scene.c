/* Stage306 verifies the ACTUAL CPU scene builder (8 BC1 color bands)
 * and varying vertex UVs; no real game assets. GPU verification separate. */
#include "stage306_patterned_gpu_scene.h"
#include <assert.h>
#include <stdint.h>
#include <stdlib.h>
#include <stdio.h>
#include <string.h>
static const uint8_t original[3][4]={
    {96,72,201,128},{232,55,28,128},{21,202,219,255}
};
static const uint16_t bands[2][4]={
    {0xf800u,0xfc00u,0x001fu,0x07ffu},
    {0x07ffu,0xf81fu,0x07e0u,0xffe0u}
};
static void expand(uint16_t v,uint8_t out[4]) {
    unsigned r=(v>>11u)&31u,g=(v>>5u)&63u,b=v&31u;
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
    for(unsigned slot=0;slot<3u;++slot) {
        b->rgba[slot]=(uint8_t*)malloc(64u*64u*4u);
        assert(b->rgba[slot]);
        for(size_t p=0;p<64u*64u*4u;p+=4u)
            memcpy(b->rgba[slot]+p,original[slot],4u);
        b->report.atlas[slot]=(FojAtlasRgba8Info){64u,64u,64u*64u*4u};
        b->batches[slot]=(FojGpuBatch){3u*slot,3u,slot};
    }
}
static void release(FojGpuPrivateBundleData *b) {
    for(unsigned i=0;i<3u;++i)free(b->rgba[i]);
    free(b->vertices);free(b->batches);
}
static void success(void) {
    FojGpuPrivateBundleData b;prepare(&b);
    uint8_t *const original0=b.rgba[0];
    assert(foj_stage306_apply_patterned_split(&b)==1);
    assert(b.rgba[0]==original0);
    assert(b.report.actor.stream.vertices_written==15u);
    assert(b.report.actor.stream.batches_written==3u);
    assert(b.batches[0].first_vertex==0u && b.batches[0].vertex_count==3u);
    assert(b.batches[1].first_vertex==3u && b.batches[1].vertex_count==6u);
    assert(b.batches[2].first_vertex==9u && b.batches[2].vertex_count==6u);
    for(unsigned side=0;side<2u;++side) {
        unsigned material=side==0u?2u:1u;
        assert(b.report.atlas[material].width==256u);
        assert(b.report.atlas[material].height==256u);
        assert(b.report.atlas[material].pixel_bytes==256u*256u*4u);
        for(unsigned y=0;y<256u;++y) {
            for(unsigned x=0;x<256u;++x) {
                uint8_t expected[4];
                expand(bands[side][x/64u],expected);
                assert(memcmp(b.rgba[material]+((size_t)y*256u+x)*4u,
                              expected,4u)==0);
            }
        }
    }
    /* A shared color across page border is intentional: cyan. */
    assert(bands[0][3]==bands[1][0]);
    /* 12 vertices: left and right quads meet at x=0. Check that
     * page-local U varies 0->1 horizontally, and V varies in Y. */
    for(unsigned start=3u;start<=9u;start+=6u) {
        assert(b.vertices[start].u==0.f);
        assert(b.vertices[start+1u].u==1.f);
        assert(b.vertices[start+2u].u==0.f);
        assert(b.vertices[start+3u].u==1.f);
        assert(b.vertices[start+4u].u==1.f);
        assert(b.vertices[start+5u].u==0.f);
        assert(b.vertices[start].v==1.f && b.vertices[start+2u].v==0.f);
    }
    assert(b.vertices[9].x==-.6f && b.vertices[3].x==0.f);
    assert(b.vertices[4].x==.6f && b.vertices[10].x==0.f);
    assert(foj_stage306_apply_patterned_split(&b)==0);
    release(&b);
}
static void refusal(void) {
    assert(foj_stage306_apply_patterned_split(NULL)==0);
    for(unsigned slot=0;slot<3u;++slot) {
        FojGpuPrivateBundleData b;prepare(&b);
        FojGpuVertex *v=b.vertices;
        uint8_t *a=b.rgba[2];
        b.rgba[slot][17]^=1u;
        assert(foj_stage306_apply_patterned_split(&b)==0);
        assert(b.rgba[2]==a && b.vertices==v);
        release(&b);
    }
    for(unsigned slot=0;slot<3u;++slot) {
        FojGpuPrivateBundleData b;prepare(&b);
        b.report.atlas[slot].width=8u;
        assert(foj_stage306_apply_patterned_split(&b)==0);
        assert(b.report.actor.stream.vertices_written==9u);
        release(&b);
    }
}
int main(void) {
    success();refusal();
    puts("STAGE306_NATIVE_EIGHT_PATTERN_BANDS_AND_INTERPOLATED_UV_PASS");
    return 0;
}
