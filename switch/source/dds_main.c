/*
 * User-local legacy DDS texture viewer, not the original FoJ 3D renderer.
 * Searches one explicitly provisioned DDS file at a fixed SD-card location;
 * the file may have the original .tga extension. No game asset is bundled.
 * If absent/invalid, it displays a generated 8x8 texture instead.
 */
#include <switch.h>
#include <stdint.h>
#include <stdlib.h>
#include <stdio.h>
#include <string.h>

#include "dds_texture.h"

enum { SCREEN_W = 1280, SCREEN_H = 720, MAX_DDS_FILE = 8388608 };
typedef struct {
    uint32_t *pixels;
    unsigned width, height;
    int real_file;
} Texture;

static void put32(uint8_t *p, uint32_t v) {
    p[0] = (uint8_t)v;
    p[1] = (uint8_t)(v >> 8);
    p[2] = (uint8_t)(v >> 16);
    p[3] = (uint8_t)(v >> 24);
}

static int generated_texture(Texture *tex) {
    uint8_t dds[128 + 8 * 8 * 4] = {0};
    memcpy(dds, "DDS ", 4);
    put32(dds + 4, 124);
    put32(dds + 8, 0x1007);
    put32(dds + 12, 8);
    put32(dds + 16, 8);
    put32(dds + 76, 32);
    put32(dds + 80, 0x41);
    put32(dds + 88, 32);
    put32(dds + 92, 0x00FF0000);
    put32(dds + 96, 0x0000FF00);
    put32(dds + 100, 0x000000FF);
    put32(dds + 104, 0xFF000000);
    for (unsigned y = 0; y < 8; ++y) {
        for (unsigned x = 0; x < 8; ++x) {
            uint8_t *p = dds + 128 + 4 * (y * 8 + x);
            p[0] = (uint8_t)(x * 34u);
            p[1] = (uint8_t)(y * 34u);
            p[2] = (uint8_t)(x * 19u + y * 12u);
            p[3] = 255;
        }
    }
    tex->pixels = malloc(8 * 8 * sizeof(uint32_t));
    if (!tex->pixels) return 0;
    FojDdsInfo info;
    if (foj_dds_decode(dds, sizeof(dds), tex->pixels, 8, 64,
                       &info) != FOJ_DDS_OK) {
        free(tex->pixels);
        tex->pixels = NULL;
        return 0;
    }
    tex->width = info.width;
    tex->height = info.height;
    tex->real_file = 0;
    return 1;
}

static int load_local_dds(const char *path, Texture *tex) {
    FILE *file = fopen(path, "rb");
    if (!file) return 0;
    int ok = 0;
    if (fseek(file, 0, SEEK_END) == 0) {
        long length = ftell(file);
        if (length >= FOJ_DDS_HEADER_BYTES &&
            length <= MAX_DDS_FILE &&
            fseek(file, 0, SEEK_SET) == 0) {
            uint8_t *bytes = malloc((size_t)length);
            if (bytes) {
                if (fread(bytes, 1, (size_t)length, file) == (size_t)length) {
                    FojDdsInfo info;
                    if (foj_dds_inspect(bytes, (size_t)length,
                                        &info) == FOJ_DDS_OK) {
                        size_t count = (size_t)info.width * (size_t)info.height;
                        if (count <= 4096u * 4096u) {
                            uint32_t *rgba = malloc(count * sizeof(*rgba));
                            if (rgba && foj_dds_decode(bytes, (size_t)length,
                                     rgba, info.width, count, &info) == FOJ_DDS_OK) {
                                tex->pixels = rgba;
                                tex->width = info.width;
                                tex->height = info.height;
                                tex->real_file = 1;
                                ok = 1;
                            } else {
                                free(rgba);
                            }
                        }
                    }
                }
                free(bytes);
            }
        }
    }
    fclose(file);
    return ok;
}

static uint32_t checker(unsigned x, unsigned y) {
    unsigned checker = ((x / 24 + y / 24) & 1u);
    return checker ? UINT32_C(0xff393b4c) : UINT32_C(0xff282b39);
}

static void draw(Texture *tex, uint32_t *screen, unsigned stride,
                 unsigned zoom, int pan_x, int pan_y) {
    /* Start from an ordinary checkerboard, then draw alpha-composited pixels.
     * Nearest-neighbor presentation only, no original game's filtering.
     */
    for (unsigned y = 0; y < SCREEN_H; ++y) {
        uint32_t *row = screen + (size_t)y * stride;
        for (unsigned x = 0; x < SCREEN_W; ++x) row[x] = checker(x, y);
    }

    const unsigned max_w = SCREEN_W - 80u, max_h = SCREEN_H - 96u;
    double fit_x = (double)max_w / tex->width;
    double fit_y = (double)max_h / tex->height;
    double scale = fit_x < fit_y ? fit_x : fit_y;
    if (scale > 16.0) scale = 16.0;
    scale *= zoom;
    double display_w = tex->width * scale;
    double display_h = tex->height * scale;
    double start_x = ((double)SCREEN_W - display_w)/2 + pan_x;
    double start_y = ((double)SCREEN_H - display_h)/2 + pan_y;

    for (unsigned y = 0; y < SCREEN_H; ++y) {
        double src_y = ((double)y - start_y)/scale;
        if (src_y < 0 || src_y >= tex->height) continue;
        unsigned sy = (unsigned)src_y;
        uint32_t *row = screen + (size_t)y * stride;
        for (unsigned x = 0; x < SCREEN_W; ++x) {
            double src_x = ((double)x - start_x)/scale;
            if (src_x < 0 || src_x >= tex->width) continue;
            unsigned sx = (unsigned)src_x;
            uint32_t color = tex->pixels[(size_t)sy * tex->width + sx];
            unsigned a = (color >> 24) & 255u;
            uint32_t bg = row[x];
            unsigned r = ((color & 255u) * a + (bg & 255u) * (255u - a)) / 255u;
            unsigned g = (((color >> 8) & 255u) * a +
                          ((bg >> 8) & 255u) * (255u - a)) / 255u;
            unsigned b = (((color >> 16) & 255u) * a +
                          ((bg >> 16) & 255u) * (255u - a)) / 255u;
            row[x] = UINT32_C(0xff000000) | (b << 16) | (g << 8) | r;
        }
    }
    const uint32_t marker = tex->real_file ?
        UINT32_C(0xff50b956) : UINT32_C(0xff5c58ed);
    for (unsigned y = 12; y < 37; ++y)
        for (unsigned x = SCREEN_W - 44; x < SCREEN_W - 16; ++x)
            screen[(size_t)y * stride + x] = marker;
}

int main(int argc, char **argv) {
    (void)argc; (void)argv;
    Texture texture = {0};
    const char *local_path = "sdmc:/switch/foj/textures/preview.tga";
    int loaded = load_local_dds(local_path, &texture);
    if (!loaded && R_SUCCEEDED(fsdevMountSdmc()))
        loaded = load_local_dds(local_path, &texture);
    if (!loaded && !generated_texture(&texture)) return 2;

    padConfigureInput(1, HidNpadStyleSet_NpadStandard);
    PadState pad;
    padInitializeDefault(&pad);

    Framebuffer framebuffer;
    Result result = framebufferCreate(&framebuffer, nwindowGetDefault(),
                                      SCREEN_W, SCREEN_H,
                                      PIXEL_FORMAT_RGBA_8888, 2);
    if (R_FAILED(result)) { free(texture.pixels); return 3; }
    result = framebufferMakeLinear(&framebuffer);
    if (R_FAILED(result)) {
        framebufferClose(&framebuffer);
        free(texture.pixels);
        return 4;
    }

    unsigned zoom = 1;
    int pan_x = 0, pan_y = 0;
    while (appletMainLoop()) {
        padUpdate(&pad);
        u64 pressed = padGetButtonsDown(&pad);
        if (pressed & HidNpadButton_Plus) break;
        if (pressed & HidNpadButton_Left) pan_x += 25;
        if (pressed & HidNpadButton_Right) pan_x -= 25;
        if (pressed & HidNpadButton_Up) pan_y += 25;
        if (pressed & HidNpadButton_Down) pan_y -= 25;
        if (pressed & HidNpadButton_ZR && zoom < 8) zoom *= 2;
        if (pressed & HidNpadButton_ZL && zoom > 1) zoom /= 2;

        u32 stride_bytes = 0;
        u32 *screen = (u32 *)framebufferBegin(&framebuffer, &stride_bytes);
        if (screen) draw(&texture, (uint32_t *)screen,
                         (unsigned)(stride_bytes/sizeof(u32)), zoom, pan_x, pan_y);
        framebufferEnd(&framebuffer);
    }
    framebufferClose(&framebuffer);
    free(texture.pixels);
    return 0;
}
