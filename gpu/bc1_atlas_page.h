#ifndef FOJ_BC1_ATLAS_PAGE_H
#define FOJ_BC1_ATLAS_PAGE_H

/* Stage301: bounded research-only BC1 1024x1024 => one 256x256 RGBA8 page.
 * No original PS3 data bundled or loaded here. The caller owns the buffer.
 * Only classic single-level DDS DXT1, no DX10, arrays, cubemaps or mips.
 * This does NOT upload pages to the GPU or map game UV coordinates.
 */
#include "atlas_dds.h"
#include <stddef.h>
#include <stdint.h>

enum {
    FOJ_BC1_SOURCE_EDGE=1024,
    FOJ_BC1_PAGE_EDGE=256,
    FOJ_BC1_PAGES_PER_SIDE=4,
    FOJ_BC1_PAGE_COUNT=16,
    FOJ_BC1_SOURCE_FILE_BYTES=128 + 1024*1024/2,
    FOJ_BC1_PAGE_DDS_BYTES=128 + 256*256/2,
    FOJ_BC1_PAGE_RGBA_BYTES=256*256*4
};

/* Returns 1 only if every header/payload bound is validated and the actual
 * foj_atlas_dds_decode succeeds. On any failure out bytes and info remain
 * unchanged; page_x/y are integer grid indices in [0,3].
 * Scratch contains only the selected page, never a 4MiB full RGBA image.
 */
int foj_bc1_1024_decode_page(const uint8_t *dds,size_t len,
                             unsigned page_x,unsigned page_y,
                             uint8_t *out,size_t cap,FojAtlasRgba8Info *info);

#endif
