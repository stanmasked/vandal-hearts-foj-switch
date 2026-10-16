/* Generated DDS fixtures: no commercial image contents. */
#include "dds_texture.h"
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

static void put32(uint8_t *p, uint32_t value) {
    p[0] = (uint8_t)value;
    p[1] = (uint8_t)(value >> 8);
    p[2] = (uint8_t)(value >> 16);
    p[3] = (uint8_t)(value >> 24);
}

static void make_header(uint8_t *dds, unsigned width, unsigned height,
                        int dxt1) {
    memset(dds, 0, 512);
    memcpy(dds, "DDS ", 4);
    put32(dds + 4, 124);
    put32(dds + 8, 0x1007);
    put32(dds + 12, height);
    put32(dds + 16, width);
    put32(dds + 76, 32);
    put32(dds + 108, 0x1000);
    if (dxt1) {
        put32(dds + 80, 0x4);
        put32(dds + 84, 0x31545844);
    } else {
        put32(dds + 80, 0x41);
        put32(dds + 88, 32);
        put32(dds + 92, 0x00FF0000);
        put32(dds + 96, 0x0000FF00);
        put32(dds + 100, 0x000000FF);
        put32(dds + 104, 0xFF000000);
    }
}

static void test_bgra8_decode(void) {
    uint8_t file[512];
    uint32_t pixels[8] = {0};
    FojDdsInfo info;
    make_header(file, 2, 2, 0);
    const uint8_t color[] = {
        10,20,30,255, 0,128,255,64,
        255,0,0,128, 100,100,100,255,
    };
    memcpy(file + 128, color, sizeof(color));
    assert(foj_dds_decode(file, 128+sizeof(color),
                          pixels, 3, 8, &info) == FOJ_DDS_OK);
    assert(info.width == 2 && info.height == 2);
    assert(info.format == FOJ_DDS_BGRA8);
    assert(info.first_level_bytes == 16);
    assert(pixels[0] == UINT32_C(0xff0a141e));
    assert(pixels[1] == UINT32_C(0x400080ff));
    assert(pixels[3] == UINT32_C(0x800000ff));
    assert(pixels[4] == UINT32_C(0xff646464));
    assert(pixels[2] == 0 && pixels[5] == 0); /* untouched stride padding */
}

static void test_dxt1_four_color_palette(void) {
    uint8_t file[512];
    uint32_t pixels[16] = {0};
    FojDdsInfo info;
    make_header(file, 4, 4, 1);
    uint8_t *block = file + 128;
    block[0] = 0x00; block[1] = 0xF8; /* 0xf800 red */
    block[2] = 0xE0; block[3] = 0x07; /* 0x07e0 green */
    /* Each row uses index 0, 1, 2, 3. */
    for (int i = 0; i < 4; ++i) block[4 + i] = 0xE4;
    assert(foj_dds_decode(file, 136, pixels, 4, 16, &info) == FOJ_DDS_OK);
    assert(info.format == FOJ_DDS_DXT1 && info.first_level_bytes == 8);
    for (int y = 0; y < 4; ++y) {
        assert(pixels[y*4+0] == UINT32_C(0xff0000ff));
        assert(pixels[y*4+1] == UINT32_C(0xff00ff00));
        assert(pixels[y*4+2] == UINT32_C(0xff0055aa));
        assert(pixels[y*4+3] == UINT32_C(0xff00aa55));
    }
}

static void test_dxt1_one_bit_alpha(void) {
    uint8_t file[512];
    uint32_t pixels[16] = {0};
    FojDdsInfo info;
    make_header(file, 4, 4, 1);
    uint8_t *block = file + 128;
    block[0] = 0x1F; block[1] = 0x00; /* blue 0x001f */
    block[2] = 0x00; block[3] = 0xF8; /* red 0xf800, c0 < c1 */
    for (int i = 0; i < 4; ++i) block[4 + i] = 0xE4;
    assert(foj_dds_decode(file, 136, pixels, 4, 16, &info) == FOJ_DDS_OK);
    assert(pixels[0] == UINT32_C(0xffff0000));
    assert(pixels[1] == UINT32_C(0xff0000ff));
    assert(pixels[2] == UINT32_C(0xff7f007f));
    assert(pixels[3] == 0);
}

static void test_dxt1_npot_and_capacity(void) {
    uint8_t file[512];
    uint32_t pixels[40];
    FojDdsInfo info;
    make_header(file, 5, 3, 1);
    memset(file + 128, 0, 16);
    /* Two DXT1 blocks, with c0=red and c1=green. */
    for (int i = 0; i < 2; ++i) {
        file[128 + i*8] = 0;
        file[129 + i*8] = 0xF8;
        file[130 + i*8] = 0xE0;
        file[131 + i*8] = 0x07;
    }
    for (int i = 0; i < 40; ++i) pixels[i] = UINT32_C(0xDEADBEEF);
    assert(foj_dds_decode(file, 144, pixels, 7, 21, &info) == FOJ_DDS_OK);
    assert(pixels[0] == UINT32_C(0xff0000ff));
    assert(pixels[4] == UINT32_C(0xff0000ff));
    assert(pixels[6] == UINT32_C(0xDEADBEEF)); /* row padding */
    assert(pixels[14] == UINT32_C(0xff0000ff));
    assert(pixels[21] == UINT32_C(0xDEADBEEF)); /* past output buffer */
    assert(foj_dds_decode(file, 144, pixels, 4, 40, &info) == FOJ_DDS_OUTPUT);
    assert(foj_dds_decode(file, 144, pixels, 7, 20, &info) == FOJ_DDS_OUTPUT);
}

static void test_malformed_headers_and_truncation(void) {
    uint8_t file[512];
    uint32_t pixels[16] = {0};
    FojDdsInfo info;
    make_header(file, 4, 4, 1);
    assert(foj_dds_inspect(NULL, 512, &info) == FOJ_DDS_ARGUMENT);
    assert(foj_dds_inspect(file, 512, NULL) == FOJ_DDS_ARGUMENT);
    assert(foj_dds_inspect(file, 127, &info) == FOJ_DDS_TRUNCATED);
    assert(foj_dds_inspect(file, 135, &info) == FOJ_DDS_TRUNCATED);
    file[0] = 'X';
    assert(foj_dds_inspect(file, 136, &info) == FOJ_DDS_HEADER);
    file[0] = 'D';
    put32(file + 84, 0x30315844); /* DX10 */
    assert(foj_dds_inspect(file, 136, &info) == FOJ_DDS_UNSUPPORTED);
    put32(file + 84, 0x31545844);
    put32(file + 16, 10000);
    assert(foj_dds_inspect(file, 136, &info) == FOJ_DDS_DIMENSIONS);
    put32(file + 16, 4);
    put32(file + 112, 0x200); /* cubemap */
    assert(foj_dds_inspect(file, 136, &info) == FOJ_DDS_UNSUPPORTED);
    put32(file + 112, 0);
    put32(file + 24, 4); /* volume */
    assert(foj_dds_inspect(file, 136, &info) == FOJ_DDS_UNSUPPORTED);
    put32(file + 24, 0);
    assert(foj_dds_decode(file, 136, NULL, 4, 16, &info) == FOJ_DDS_ARGUMENT);
}

int main(void) {
    test_bgra8_decode();
    test_dxt1_four_color_palette();
    test_dxt1_one_bit_alpha();
    test_dxt1_npot_and_capacity();
    test_malformed_headers_and_truncation();
    puts("DDS BGRA8/DXT1: five synthetic test scenarios passed");
    return 0;
}
