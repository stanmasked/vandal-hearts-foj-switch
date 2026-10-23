#ifndef FOJ_STAGE332_DDS_SOURCE_H
#define FOJ_STAGE332_DDS_SOURCE_H
/* Synthetic-tested, owner-local, read-only DDS byte decoder.
 * No PKG content, decryption keys, file I/O or GPU upload is included. */
#include <stddef.h>
#include <stdint.h>

enum {
    FOJ_STAGE332_MAX_DIMENSION = 2048,
    FOJ_STAGE332_MAX_PIXELS = 2048 * 2048,
    FOJ_STAGE332_MAX_MIPS = 12
};

typedef enum {
    FOJ_STAGE332_BGRA8 = 1,
    FOJ_STAGE332_BGR8 = 2,
    FOJ_STAGE332_BC1 = 3,
    FOJ_STAGE332_BC2 = 4
} FojStage332Format;

typedef struct {
    uint32_t width, height, mip_levels;
    FojStage332Format format;
    size_t rgba_bytes;
} FojStage332DdsInfo;

/* Validates strict classic DDS masks, flags, dimensions, mip-chain extents
 * and exact file length, including all mip levels. Does not write on refusal. */
int foj_stage332_dds_inspect(const uint8_t *dds, size_t len,
                             FojStage332DdsInfo *out_info);
/* Decodes only level zero into caller-owned RGBA8. Source and output must
 * not overlap. On any failure out_pixels AND out_info remain unchanged. */
int foj_stage332_dds_decode(const uint8_t *dds, size_t len,
                            uint8_t *out_pixels, size_t capacity,
                            FojStage332DdsInfo *out_info);
#endif
