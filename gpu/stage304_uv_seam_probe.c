#include "stage304_uv_seam_probe.h"
#include "bc1_atlas_page.h"
#include <stdlib.h>
#include <string.h>

enum { GENERATED_SLOTLEN=64*64*4,
       SOURCE_LEN=FOJ_BC1_SOURCE_FILE_BYTES };
static const unsigned char exact_generated[3][4]={
    {96,72,201,128}, {232,55,28,128}, {21,202,219,255}
};
static int exact_stage293(const FojGpuPrivateBundleData *b) {
    if (!b || b->report.atlas_count!=3u)return 0;
    for (unsigned i=0;i<3u;++i) {
        if (!b->rgba[i] || b->report.atlas[i].width!=64u ||
            b->report.atlas[i].height!=64u ||
            b->report.atlas[i].pixel_bytes!=GENERATED_SLOTLEN)
            return 0;
        for (size_t p=0;p<GENERATED_SLOTLEN;p+=4u)
            if (memcmp(b->rgba[i]+p,exact_generated[i],4u))return 0;
    }
    return 1;
}
static void le32(unsigned char *p,unsigned n) {
    p[0]=(unsigned char)n;p[1]=(unsigned char)(n>>8u);
    p[2]=(unsigned char)(n>>16u);p[3]=(unsigned char)(n>>24u);
}
int foj_stage304_apply_seam_probe(FojGpuPrivateBundleData *bundle,
                                  unsigned side,FojBc1PageUv *receipt) {
    if (!receipt || side>FOJ_STAGE304_RIGHT || !exact_stage293(bundle))
        return 0;
    /* IEEE-754 texel centers adjacent across 0.5 UV seam. */
    const float u=(side==FOJ_STAGE304_LEFT?511.5f:512.5f)/1024.0f;
    const float v=384.5f/1024.0f;
    FojBc1PageUv resolved={0};
    if (!foj_bc1_1024_resolve_uv(u,v,&resolved) ||
        resolved.page_x!=1u+side || resolved.page_y!=1u ||
        resolved.local_x!=(side==FOJ_STAGE304_LEFT?255u:0u) ||
        resolved.local_y!=128u)return 0;

    unsigned char *src=(unsigned char*)malloc(SOURCE_LEN);
    if (!src)return 0;
    memset(src,0,128u);
    memcpy(src,"DDS ",4u);
    le32(src+4u,124u);le32(src+8u,0x81007u);
    le32(src+12u,1024u);le32(src+16u,1024u);
    le32(src+20u,1024u*1024u/2u);le32(src+28u,1u);
    le32(src+76u,32u);le32(src+80u,4u);
    le32(src+84u,0x31545844u);le32(src+108u,0x1000u);
    for (unsigned row=0;row<256u;++row) {
        for (unsigned col=0;col<256u;++col) {
            const unsigned px=col/64u,py=row/64u;
            const unsigned short endpoint=(py==1u && px==1u)?
                0x163au:(py==1u && px==2u)?0x1e5bu:0xf800u;
            const size_t at=128u+((size_t)row*256u+col)*8u;
            src[at]=(unsigned char)endpoint;
            src[at+1u]=(unsigned char)(endpoint>>8u);
            src[at+2u]=0x1fu;src[at+3u]=0u;
            memset(src+at+4u,0,4u);
        }
    }
    unsigned char *out=(unsigned char*)malloc(FOJ_BC1_PAGE_RGBA_BYTES);
    if (!out) {free(src);return 0;}
    FojAtlasRgba8Info size={0};
    const int ok=foj_bc1_1024_decode_page(
        src,SOURCE_LEN,resolved.page_x,resolved.page_y,out,
        FOJ_BC1_PAGE_RGBA_BYTES,&size);
    free(src);
    if (!ok || size.width!=256u || size.height!=256u ||
        size.pixel_bytes!=FOJ_BC1_PAGE_RGBA_BYTES) {
        free(out);return 0;
    }
    const unsigned char wanted[4]={
        side==FOJ_STAGE304_LEFT?16u:24u,
        side==FOJ_STAGE304_LEFT?199u:203u,
        side==FOJ_STAGE304_LEFT?214u:222u,
        255u
    };
    for (size_t p=0;p<FOJ_BC1_PAGE_RGBA_BYTES;p+=4u)
        if (memcmp(out+p,wanted,4u)) {free(out);return 0;}
    free(bundle->rgba[2]);
    bundle->rgba[2]=out;
    bundle->report.atlas[2]=size;
    *receipt=resolved;
    return 1;
}
