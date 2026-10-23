#include "stage332_dds_source.h"
#include <stdint.h>
#include <string.h>

static uint32_t rd32(const uint8_t *p) {
    return (uint32_t)p[0] | ((uint32_t)p[1] << 8) |
           ((uint32_t)p[2] << 16) | ((uint32_t)p[3] << 24);
}
static uint16_t rd16(const uint8_t *p) {
    return (uint16_t)((uint16_t)p[0] | ((uint16_t)p[1] << 8));
}

static size_t level_bytes(uint32_t w, uint32_t h, FojStage332Format fmt) {
    if (fmt == FOJ_STAGE332_BGRA8 || fmt == FOJ_STAGE332_BGR8)
        return (size_t)w * h * (fmt == FOJ_STAGE332_BGRA8 ? 4u : 3u);
    return (size_t)((w + 3u) / 4u) * ((h + 3u) / 4u) *
           (fmt == FOJ_STAGE332_BC1 ? 8u : 16u);
}

int foj_stage332_dds_inspect(const uint8_t *d, size_t len,
                             FojStage332DdsInfo *out_info) {
    if (!d || !out_info || len < 128 || memcmp(d, "DDS ", 4) != 0 ||
        rd32(d + 4) != 124 || rd32(d + 76) != 32 ||
        rd32(d + 24) != 0 || rd32(d + 112) != 0 ||
        rd32(d + 116) != 0 || rd32(d + 120) != 0 ||
        rd32(d + 124) != 0)
        return 0;
    const uint32_t w = rd32(d + 16), h = rd32(d + 12);
    if (!w || !h || w > FOJ_STAGE332_MAX_DIMENSION ||
        h > FOJ_STAGE332_MAX_DIMENSION ||
        (uint64_t)w * h > FOJ_STAGE332_MAX_PIXELS)
        return 0;
    const uint32_t flags = rd32(d + 80), fourcc = rd32(d + 84);
    FojStage332Format fmt;
    if (flags == 0x41u && fourcc == 0 && rd32(d + 88) == 32u &&
        rd32(d + 92) == 0x00ff0000u && rd32(d + 96) == 0x0000ff00u &&
        rd32(d + 100) == 0x000000ffu && rd32(d + 104) == 0xff000000u)
        fmt = FOJ_STAGE332_BGRA8;
    else if (flags == 0x40u && fourcc == 0 && rd32(d + 88) == 24u &&
             rd32(d + 92) == 0x00ff0000u && rd32(d + 96) == 0x0000ff00u &&
             rd32(d + 100) == 0x000000ffu && rd32(d + 104) == 0)
        fmt = FOJ_STAGE332_BGR8;
    else if (flags == 0x4u && fourcc == 0x31545844u &&
             rd32(d + 88) == 0 && rd32(d + 92) == 0 &&
             rd32(d + 96) == 0 && rd32(d + 100) == 0 && rd32(d + 104) == 0)
        fmt = FOJ_STAGE332_BC1;
    else if (flags == 0x4u && fourcc == 0x33545844u &&
             rd32(d + 88) == 0 && rd32(d + 92) == 0 &&
             rd32(d + 96) == 0 && rd32(d + 100) == 0 && rd32(d + 104) == 0)
        fmt = FOJ_STAGE332_BC2;
    else return 0;
    const uint32_t raw_mips = rd32(d + 28);
    const uint32_t mips = raw_mips ? raw_mips : 1u;
    if (mips > FOJ_STAGE332_MAX_MIPS) return 0;
    uint32_t max_mips = 1u, tw = w, th = h;
    while (tw > 1u || th > 1u) {
        tw = tw > 1u ? tw / 2u : 1u;
        th = th > 1u ? th / 2u : 1u;
        ++max_mips;
    }
    if (mips > max_mips) return 0;
    const int multi = mips > 1u;
    const int raw = fmt == FOJ_STAGE332_BGRA8 || fmt == FOJ_STAGE332_BGR8;
    const uint32_t expected_flags = (raw ? 0x100fu : 0x81007u) |
                                    (multi ? 0x20000u : 0u);
    if (rd32(d + 8) != expected_flags ||
        rd32(d + 108) != (multi ? 0x401008u : 0x1000u)) return 0;
    const size_t base = level_bytes(w, h, fmt);
    const uint32_t pitch = raw ? w * (fmt == FOJ_STAGE332_BGRA8 ? 4u : 3u)
                               : (uint32_t)base;
    if (rd32(d + 20) != pitch) return 0;
    size_t total = 128;
    tw = w; th = h;
    for (uint32_t level = 0; level < mips; ++level) {
        size_t bytes = level_bytes(tw, th, fmt);
        if (bytes > len - total) return 0;
        total += bytes;
        tw = tw > 1u ? tw / 2u : 1u;
        th = th > 1u ? th / 2u : 1u;
    }
    if (total != len) return 0;
    const FojStage332DdsInfo info = {w, h, mips, fmt, (size_t)w * h * 4u};
    *out_info = info;
    return 1;
}

static void expand565(uint16_t v, uint8_t *c) {
    unsigned r = (v >> 11) & 31u, g = (v >> 5) & 63u, b = v & 31u;
    c[0] = (uint8_t)((r << 3) | (r >> 2));
    c[1] = (uint8_t)((g << 2) | (g >> 4));
    c[2] = (uint8_t)((b << 3) | (b >> 2));
    c[3] = 255;
}
static void colors(const uint8_t *p, int bc2, uint8_t c[4][4]) {
    const uint16_t a = rd16(p), b = rd16(p + 2);
    expand565(a, c[0]); expand565(b, c[1]);
    for (unsigned k = 0; k < 3; ++k) {
        if (bc2 || a > b) {
            c[2][k] = (uint8_t)((2u * c[0][k] + c[1][k]) / 3u);
            c[3][k] = (uint8_t)((c[0][k] + 2u * c[1][k]) / 3u);
        } else c[2][k] = (uint8_t)((c[0][k] + c[1][k]) / 2u);
    }
    c[2][3] = 255;
    if (!bc2 && a <= b) memset(c[3], 0, 4);
    else c[3][3] = 255;
}
int foj_stage332_dds_decode(const uint8_t *d, size_t len,
                            uint8_t *dst, size_t capacity,
                            FojStage332DdsInfo *out_info) {
    FojStage332DdsInfo info;
    if (!dst || !out_info || !foj_stage332_dds_inspect(d, len, &info) ||
        capacity < info.rgba_bytes) return 0;
    /* Strictly forbid in-place or partially overlapping decoding. */
    const uintptr_t src_addr = (uintptr_t)d, dst_addr = (uintptr_t)dst;
    if (src_addr > UINTPTR_MAX - len ||
        dst_addr > UINTPTR_MAX - info.rgba_bytes ||
        (src_addr < dst_addr + info.rgba_bytes && dst_addr < src_addr + len))
        return 0;
    const uint32_t w = info.width, h = info.height;
    const uint8_t *src = d + 128;
    if (info.format == FOJ_STAGE332_BGRA8 || info.format == FOJ_STAGE332_BGR8) {
        const unsigned step = info.format == FOJ_STAGE332_BGRA8 ? 4u : 3u;
        for (size_t i = 0; i < (size_t)w * h; ++i) {
            dst[4 * i] = src[step * i + 2];
            dst[4 * i + 1] = src[step * i + 1];
            dst[4 * i + 2] = src[step * i];
            dst[4 * i + 3] = step == 4u ? src[step * i + 3] : 255;
        }
    } else {
        const int bc2 = info.format == FOJ_STAGE332_BC2;
        const size_t bw = (w + 3u) / 4u, bh = (h + 3u) / 4u;
        const size_t block_size = bc2 ? 16u : 8u;
        for (size_t by = 0; by < bh; ++by) for (size_t bx = 0; bx < bw; ++bx) {
            const uint8_t *block = src + (by * bw + bx) * block_size;
            const uint8_t *cp = block + (bc2 ? 8u : 0u);
            uint8_t c[4][4];
            colors(cp, bc2, c);
            const uint32_t indices = rd32(cp + 4);
            for (unsigned i = 0; i < 16u; ++i) {
                const size_t x = bx * 4u + (i & 3u), y = by * 4u + (i >> 2);
                if (x >= w || y >= h) continue;
                uint8_t *px = dst + (y * w + x) * 4u;
                memcpy(px, c[(indices >> (i * 2u)) & 3u], 4u);
                if (bc2) px[3] = (uint8_t)(((block[i / 2u] >> ((i & 1u) * 4u)) & 15u) * 17u);
            }
        }
    }
    *out_info = info;
    return 1;
}
