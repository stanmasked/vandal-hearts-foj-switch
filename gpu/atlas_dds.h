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
    FOJ_ATLAS_MAX_BYTES=256*256*4,
    FOJ_ATLAS_MAX_MIP_LEVELS=9,
    /* Full RGBA8 256x256 mip chain is smaller than 1.5x the base. */
    FOJ_ATLAS_MAX_INPUT_BYTES=256*256*4+256*256*2
};
typedef struct {
    unsigned width,height;
    size_t pixel_bytes;
} FojAtlasRgba8Info;

/* Classic DDS only (no DX10, arrays, cubemaps or PS3 swizzling).
 * Input: raw RGBA8/BGRA8, BC1/DXT1 or BC3/DXT5; output is RGBA8 bytes.
 * Width 8..256 multiple of 8; height 1..256, multiple of 4 for BCn.
 * Validates an exact complete mip chain when present, but decodes only
 * level 0. GPU mip filtering/upload remains disabled.
 * On any failure, preserves all output bytes and metadata. */
int foj_atlas_dds_decode(const uint8_t *dds,size_t len,
                         uint8_t *out,size_t cap,FojAtlasRgba8Info *info);

/* 1 = loaded; 0 = file absent (ENOENT); -1 = rejected or I/O failed.
 * Input is size-bounded, read twice and compared on the same open stream,
 * checked for growth/truncation, and closed before RGBA8 decode.
 * Never modifies outputs on 0 or -1. This best-effort replay is not an
 * adversarial concurrent-write proof or an on-console verification. */
int foj_atlas_dds_try_read(const char *path,uint8_t *out,size_t cap,
                           FojAtlasRgba8Info *info);
#endif
