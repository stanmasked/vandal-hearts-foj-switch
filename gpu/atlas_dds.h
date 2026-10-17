#ifndef FOJ_ATLAS_DDS_H
#define FOJ_ATLAS_DDS_H
/* Private-user local DDS intake: strict RGBA8, BC1/DXT1 and BC3/DXT5 subset.
 * No PS3 files, codecs, encryption keys or bundled game content. */
#include <stddef.h>
#include <stdint.h>
enum {
    FOJ_ATLAS_DDS_HEADER_BYTES=128,
    FOJ_ATLAS_MAX_WIDTH=256,
    FOJ_ATLAS_MAX_HEIGHT=256,
    FOJ_ATLAS_MAX_BYTES=256*256*4
};
typedef struct {
    unsigned width,height;
    size_t pixel_bytes;
} FojAtlasRgba8Info;

/* Classic DDS only (no DX10, mipmaps, arrays, cubemaps or swizzling).
 * Input: raw RGBA8, BC1/DXT1 or BC3/DXT5; output is RGBA8 bytes.
 * Width 8..256 multiple of 8; height 1..256, multiple of 4 for BCn.
 * Strict pitch/linear-size, header masks and exact payload length.
 * On any failure, preserves all output bytes and metadata. */
int foj_atlas_dds_decode(const uint8_t *dds,size_t len,
                         uint8_t *out,size_t cap,FojAtlasRgba8Info *info);

/* 1 = loaded; 0 = file absent (ENOENT); -1 = rejected or I/O failed.
 * Never modifies outputs on 0 or -1. Files larger than max are rejected. */
int foj_atlas_dds_try_read(const char *path,uint8_t *out,size_t cap,
                           FojAtlasRgba8Info *info);
#endif
