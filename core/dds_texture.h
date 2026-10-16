#ifndef FOJ_DDS_TEXTURE_H
#define FOJ_DDS_TEXTURE_H

/* Small, dependency-free legacy DDS decoder for original FoJ research.
 * Supports uncompressed BGRA8 and DXT1/BC1 base-level textures only.
 * It does not decode arbitrary DDS/DX10, volume, cube-map, or PS3 swizzle
 * layouts. No commercial texture data is embedded in this module.
 */
#include <stddef.h>
#include <stdint.h>

enum {
    FOJ_DDS_HEADER_BYTES = 128,
    FOJ_DDS_MAX_DIMENSION = 4096
};

typedef enum {
    FOJ_DDS_OK = 0,
    FOJ_DDS_ARGUMENT,
    FOJ_DDS_HEADER,
    FOJ_DDS_UNSUPPORTED,
    FOJ_DDS_DIMENSIONS,
    FOJ_DDS_TRUNCATED,
    FOJ_DDS_OUTPUT
} FojDdsStatus;

typedef enum {
    FOJ_DDS_BGRA8 = 1,
    FOJ_DDS_DXT1 = 2
} FojDdsFormat;

typedef struct {
    uint32_t width, height;
    uint32_t mip_count;      /* declared mips; decoder reads only level zero */
    FojDdsFormat format;
    size_t first_level_bytes; /* DDS data required after 128-byte header */
} FojDdsInfo;

/* No file extension dependence: "DDS " magic is mandatory. */
FojDdsStatus foj_dds_inspect(const uint8_t *data, size_t length,
                             FojDdsInfo *info);

/* Caller allocates at least height * stride_pixels uint32_t pixels.
 * Output pixel representation: 0xAABBGGRR, matching libnx RGBA_8888.
 * Rows in the caller buffer may have padding; this function never writes it.
 */
FojDdsStatus foj_dds_decode(const uint8_t *data, size_t length,
                            uint32_t *rgba, size_t stride_pixels,
                            size_t capacity_pixels, FojDdsInfo *info);

const char *foj_dds_error(FojDdsStatus code);

#endif
