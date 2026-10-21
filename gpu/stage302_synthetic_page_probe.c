#include "stage302_synthetic_page_probe.h"
#include "bc1_atlas_page.h"
#include <stdlib.h>
#include <string.h>

/* DXT1 solid-color 565 blue-green, quantized near the Stage266 COOL probe.
 * Every other page is RED, so selecting wrong (x,y) is a visible failure. */
enum {
    GENERATED_SLOTLEN=64*64*4,
    GENERATED_SOURCE_BYTES=FOJ_BC1_SOURCE_FILE_BYTES
};
static const uint8_t expected_slots[3][4]={
    {96,72,201,128},{232,55,28,128},{21,202,219,255}
};

static int assert_generated_stage293(const FojGpuPrivateBundleData *bundle) {
    if (!bundle || bundle->report.atlas_count!=3u)return 0;
    for (unsigned slot=0;slot<3u;++slot) {
        if (!bundle->rgba[slot] ||
            bundle->report.atlas[slot].width!=64u ||
            bundle->report.atlas[slot].height!=64u ||
            bundle->report.atlas[slot].pixel_bytes!=GENERATED_SLOTLEN)
            return 0;
        for (size_t i=0;i<GENERATED_SLOTLEN;i+=4u)
            if (memcmp(bundle->rgba[slot]+i,expected_slots[slot],4u))
                return 0;
    }
    return 1;
}
static void le32(uint8_t *p,uint32_t value) {
    p[0]=(uint8_t)value;p[1]=(uint8_t)(value>>8);
    p[2]=(uint8_t)(value>>16);p[3]=(uint8_t)(value>>24);
}
int foj_stage302_apply_generated_page(FojGpuPrivateBundleData *bundle) {
    if (!assert_generated_stage293(bundle))return 0;
    uint8_t *source=(uint8_t*)malloc(GENERATED_SOURCE_BYTES);
    if (!source)return 0;
    memset(source,0,128u);
    memcpy(source,"DDS ",4u);
    le32(source+4,124u);
    le32(source+8,0x81007u);
    le32(source+12,1024u);le32(source+16,1024u);
    le32(source+20,1024u*1024u/2u);
    le32(source+28,1u);
    le32(source+76,32u);
    le32(source+80,4u);
    le32(source+84,0x31545844u);
    le32(source+108,0x1000u);
    /* 1024/4=256 block cols; 256/4=64 cols per one page. */
    for (unsigned row=0;row<256u;++row) {
        for (unsigned col=0;col<256u;++col) {
            const int selected=(col/64u==FOJ_STAGE302_PAGE_X &&
                                row/64u==FOJ_STAGE302_PAGE_Y);
            const uint16_t color=selected?0x1e5bu:0xf800u;
            const size_t pos=128u+((size_t)row*256u+col)*8u;
            source[pos]=(uint8_t)color;
            source[pos+1]=(uint8_t)(color>>8);
            source[pos+2]=0x1fu;source[pos+3]=0x00u; /* blue 565 */
            memset(source+pos+4,0,4u); /* all texels use endpoint 0 */
        }
    }
    uint8_t *page=(uint8_t*)malloc(FOJ_BC1_PAGE_RGBA_BYTES);
    if (!page) {
        free(source);
        return 0;
    }
    FojAtlasRgba8Info info={0};
    const int decoded=foj_bc1_1024_decode_page(
        source,GENERATED_SOURCE_BYTES,
        FOJ_STAGE302_PAGE_X,FOJ_STAGE302_PAGE_Y,
        page,FOJ_BC1_PAGE_RGBA_BYTES,&info);
    free(source);
    if (!decoded || info.width!=256u || info.height!=256u ||
        info.pixel_bytes!=FOJ_BC1_PAGE_RGBA_BYTES) {
        free(page);return 0;
    }
    static const uint8_t rgba[4]={
        FOJ_STAGE302_REAR_R,FOJ_STAGE302_REAR_G,FOJ_STAGE302_REAR_B,255u
    };
    for (size_t i=0;i<FOJ_BC1_PAGE_RGBA_BYTES;i+=4u) {
        if (memcmp(page+i,rgba,4u)) {
            free(page);
            return 0;
        }
    }
    /* Swap only AFTER all generated-source and C-decoder checks pass.
     * Stage259's private bundle free owns and releases the new page. */
    free(bundle->rgba[2]);
    bundle->rgba[2]=page;
    bundle->report.atlas[2]=info;
    return 1;
}
