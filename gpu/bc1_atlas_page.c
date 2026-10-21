#include "bc1_atlas_page.h"
#include <stdlib.h>
#include <string.h>

/* The format fields are validated before reading any source block.
 * These restrictions match Stage300's documented 1024x1024 BC1 envelope;
 * original owner-private DDS headers have NOT been independently rechecked. */
static uint32_t le32(const uint8_t *p) {
    return (uint32_t)p[0] | ((uint32_t)p[1]<<8) |
           ((uint32_t)p[2]<<16) | ((uint32_t)p[3]<<24);
}
static void store32(uint8_t *p,uint32_t value) {
    p[0]=(uint8_t)value;p[1]=(uint8_t)(value>>8);
    p[2]=(uint8_t)(value>>16);p[3]=(uint8_t)(value>>24);
}
static int header_supported(const uint8_t *src,size_t len) {
    if (!src||len!=FOJ_BC1_SOURCE_FILE_BYTES||
        memcmp(src,"DDS ",4)!=0||le32(src+4)!=124 ||
        le32(src+8)!=0x81007u||
        le32(src+12)!=FOJ_BC1_SOURCE_EDGE||
        le32(src+16)!=FOJ_BC1_SOURCE_EDGE||
        le32(src+20)!=(1024u*1024u/2u)||
        le32(src+24)!=0||le32(src+28)!=1 ||
        le32(src+76)!=32||le32(src+80)!=4||
        le32(src+84)!=0x31545844u|| /* DXT1 */
        le32(src+88)!=0||le32(src+92)!=0||le32(src+96)!=0||
        le32(src+100)!=0||le32(src+104)!=0||
        le32(src+108)!=0x1000u||
        le32(src+112)!=0||le32(src+116)!=0||
        le32(src+120)!=0||le32(src+124)!=0)
        return 0;
    return 1;
}

int foj_bc1_1024_decode_page(const uint8_t *dds,size_t len,
                             unsigned page_x,unsigned page_y,
                             uint8_t *out,size_t cap,FojAtlasRgba8Info *info) {
    if (!dds||!out||!info||
        page_x>=FOJ_BC1_PAGES_PER_SIDE||
        page_y>=FOJ_BC1_PAGES_PER_SIDE||
        cap<FOJ_BC1_PAGE_RGBA_BYTES||
        !header_supported(dds,len))return 0;

    /* 32,896-byte temporary DDS rather than a 4MiB whole-atlas RGBA decode.
     * Build a canonical 256x256 BC1 header, copy 64 block rows × 64 blocks
     * from the 1024x1024 compressed source, then call the ACTUAL atlas C
     * decoder. The 1024 source stays compressed in the caller's ownership. */
    uint8_t *page=(uint8_t*)malloc(FOJ_BC1_PAGE_DDS_BYTES);
    if (!page)return 0;
    memset(page,0,128);
    memcpy(page,"DDS ",4);
    store32(page+4,124);
    store32(page+8,0x81007u);
    store32(page+12,FOJ_BC1_PAGE_EDGE);
    store32(page+16,FOJ_BC1_PAGE_EDGE);
    store32(page+20,FOJ_BC1_PAGE_EDGE*FOJ_BC1_PAGE_EDGE/2u);
    store32(page+28,1);
    store32(page+76,32);
    store32(page+80,4);
    store32(page+84,0x31545844u);
    store32(page+108,0x1000u);
    const size_t full_blocks_row=FOJ_BC1_SOURCE_EDGE/4u;
    const size_t page_blocks_row=FOJ_BC1_PAGE_EDGE/4u;
    for (size_t row=0;row<page_blocks_row;++row) {
        const size_t source_block_row=
            (size_t)page_y*page_blocks_row+row;
        const size_t source_block_col=
            (size_t)page_x*page_blocks_row;
        const size_t input_offset=128u+
            (source_block_row*full_blocks_row+source_block_col)*8u;
        const size_t output_offset=128u+row*page_blocks_row*8u;
        memcpy(page+output_offset,dds+input_offset,page_blocks_row*8u);
    }
    const int ok=foj_atlas_dds_decode(
        page,FOJ_BC1_PAGE_DDS_BYTES,out,cap,info);
    free(page);
    return ok;
}
