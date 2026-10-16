#include "dds_texture.h"

#include <stdint.h>
#include <string.h>

enum {
    DDPF_ALPHAPIXELS = 0x1,
    DDPF_FOURCC = 0x4,
    DDPF_RGB = 0x40,
    DDSCAPS2_CUBEMAP = 0x200,
    DDSCAPS2_VOLUME = 0x200000,
    DXT1_FOURCC = 0x31545844
};

static uint32_t load32(const uint8_t *p) {
    return (uint32_t)p[0] |
           ((uint32_t)p[1] << 8) |
           ((uint32_t)p[2] << 16) |
           ((uint32_t)p[3] << 24);
}

static uint16_t load16(const uint8_t *p) {
    return (uint16_t)((uint16_t)p[0] | ((uint16_t)p[1] << 8));
}

static uint32_t rgba(unsigned r, unsigned g, unsigned b, unsigned a) {
    return (uint32_t)(r | (g << 8) | (b << 16) | (a << 24));
}

static unsigned expand5(unsigned v) { return (v << 3) | (v >> 2); }
static unsigned expand6(unsigned v) { return (v << 2) | (v >> 4); }

FojDdsStatus foj_dds_inspect(const uint8_t *data, size_t length,
                             FojDdsInfo *info) {
    if (!data || !info) return FOJ_DDS_ARGUMENT;
    memset(info, 0, sizeof(*info));
    if (length < FOJ_DDS_HEADER_BYTES) return FOJ_DDS_TRUNCATED;
    if (memcmp(data, "DDS ", 4) != 0 ||
        load32(data + 4) != 124 ||
        load32(data + 76) != 32) return FOJ_DDS_HEADER;

    const uint32_t h = load32(data + 12);
    const uint32_t w = load32(data + 16);
    const uint32_t depth = load32(data + 24);
    const uint32_t caps2 = load32(data + 112);
    if (!w || !h || w > FOJ_DDS_MAX_DIMENSION || h > FOJ_DDS_MAX_DIMENSION)
        return FOJ_DDS_DIMENSIONS;
    if (depth > 1 || (caps2 & (DDSCAPS2_CUBEMAP | DDSCAPS2_VOLUME)))
        return FOJ_DDS_UNSUPPORTED;

    const uint32_t pixel_flags = load32(data + 80);
    const uint32_t fourcc = load32(data + 84);
    const uint32_t bits = load32(data + 88);
    size_t needed = 0;
    FojDdsFormat fmt;

    if (pixel_flags & DDPF_FOURCC) {
        if (fourcc != DXT1_FOURCC) return FOJ_DDS_UNSUPPORTED;
        fmt = FOJ_DDS_DXT1;
        needed = (size_t)((w + 3) / 4) * (size_t)((h + 3) / 4) * 8u;
    } else if ((pixel_flags & DDPF_RGB) && bits == 32 &&
               load32(data + 92) == 0x00FF0000u &&
               load32(data + 96) == 0x0000FF00u &&
               load32(data + 100) == 0x000000FFu &&
               load32(data + 104) == 0xFF000000u &&
               (pixel_flags & DDPF_ALPHAPIXELS)) {
        fmt = FOJ_DDS_BGRA8;
        needed = (size_t)w * (size_t)h * 4u;
    } else {
        return FOJ_DDS_UNSUPPORTED;
    }
    if (needed > length - FOJ_DDS_HEADER_BYTES) return FOJ_DDS_TRUNCATED;
    info->width = w;
    info->height = h;
    info->mip_count = load32(data + 28);
    info->format = fmt;
    info->first_level_bytes = needed;
    return FOJ_DDS_OK;
}

static void decode_block(const uint8_t *source,
                         uint32_t *out, size_t stride,
                         unsigned bx, unsigned by,
                         unsigned width, unsigned height) {
    uint32_t palette[4];
    const unsigned c0 = load16(source);
    const unsigned c1 = load16(source + 2);
    unsigned r0 = expand5((c0 >> 11) & 31u);
    unsigned g0 = expand6((c0 >> 5) & 63u);
    unsigned b0 = expand5(c0 & 31u);
    unsigned r1 = expand5((c1 >> 11) & 31u);
    unsigned g1 = expand6((c1 >> 5) & 63u);
    unsigned b1 = expand5(c1 & 31u);
    palette[0] = rgba(r0, g0, b0, 255);
    palette[1] = rgba(r1, g1, b1, 255);
    if (c0 > c1) {
        palette[2] = rgba((2*r0 + r1)/3, (2*g0 + g1)/3,
                          (2*b0 + b1)/3, 255);
        palette[3] = rgba((r0 + 2*r1)/3, (g0 + 2*g1)/3,
                          (b0 + 2*b1)/3, 255);
    } else {
        palette[2] = rgba((r0 + r1)/2, (g0 + g1)/2,
                          (b0 + b1)/2, 255);
        palette[3] = 0u; /* DXT1 one-bit transparency mode. */
    }
    const uint32_t indices = load32(source + 4);
    for (unsigned dy = 0; dy < 4; ++dy) {
        const unsigned y = by*4 + dy;
        if (y >= height) break;
        for (unsigned dx = 0; dx < 4; ++dx) {
            const unsigned x = bx*4 + dx;
            if (x < width) {
                unsigned index = (indices >> (2*(dy*4 + dx))) & 3u;
                out[(size_t)y * stride + x] = palette[index];
            }
        }
    }
}

FojDdsStatus foj_dds_decode(const uint8_t *data, size_t length,
                            uint32_t *out, size_t stride,
                            size_t capacity, FojDdsInfo *info) {
    if (!data || !out || !info) return FOJ_DDS_ARGUMENT;
    FojDdsStatus result = foj_dds_inspect(data, length, info);
    if (result != FOJ_DDS_OK) return result;
    if (stride < info->width ||
        (size_t)info->height > capacity / stride) return FOJ_DDS_OUTPUT;

    const uint8_t *source = data + FOJ_DDS_HEADER_BYTES;
    if (info->format == FOJ_DDS_BGRA8) {
        for (size_t y = 0; y < info->height; ++y) {
            for (size_t x = 0; x < info->width; ++x) {
                const uint8_t *p = source + 4 * (y*info->width + x);
                out[y*stride + x] = rgba(p[2], p[1], p[0], p[3]);
            }
        }
    } else {
        const unsigned blocks_x = (info->width + 3) / 4;
        const unsigned blocks_y = (info->height + 3) / 4;
        for (unsigned by = 0; by < blocks_y; ++by)
            for (unsigned bx = 0; bx < blocks_x; ++bx)
                decode_block(source + 8*((size_t)by*blocks_x + bx), out,
                             stride, bx, by, info->width, info->height);
    }
    return FOJ_DDS_OK;
}

const char *foj_dds_error(FojDdsStatus status) {
    switch (status) {
        case FOJ_DDS_OK: return "OK";
        case FOJ_DDS_ARGUMENT: return "Invalid argument";
        case FOJ_DDS_HEADER: return "Not legacy DDS or malformed header";
        case FOJ_DDS_UNSUPPORTED: return "Unsupported DDS format";
        case FOJ_DDS_DIMENSIONS: return "Unsafe/unsupported dimensions";
        case FOJ_DDS_TRUNCATED: return "Truncated DDS data";
        case FOJ_DDS_OUTPUT: return "Output pixel buffer too small";
        default: return "Unknown DDS error";
    }
}
