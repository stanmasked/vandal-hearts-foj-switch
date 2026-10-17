#ifndef FOJ_ATLAS_DDS_H
#define FOJ_ATLAS_DDS_H
/* Private-user local DDS intake: strict uncompressed RGBA8 subset only.
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

/* Only classic DDS (no DX10, BCn, mipmaps, arrays or cubemaps), RGBA8
 * little-endian byte order, row pitch width*4, width multiple of 8.
 * On failure, does NOT modify out pixels or info. */
int foj_atlas_dds_decode(const uint8_t *dds,size_t len,
                         uint8_t *out,size_t cap,FojAtlasRgba8Info *info);

/* 1 = loaded; 0 = file absent (ENOENT); -1 = rejected or I/O failed.
 * Never modifies outputs on 0 or -1. Files larger than max are rejected. */
int foj_atlas_dds_try_read(const char *path,uint8_t *out,size_t cap,
                           FojAtlasRgba8Info *info);
#endif
