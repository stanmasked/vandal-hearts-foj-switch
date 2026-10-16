/*
 * Independent Nintendo Switch COLL-data viewer.
 *
 * Reads an original FoJ .coll file ONLY if the user explicitly places a
 * local copy on SD card. Falls back to generated test values otherwise.
 * Neither the game, models, textures nor original tactical code are bundled.
 */
#include <switch.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>

#include "coll_grid.h"
#include "coll_view.h"

enum { FB_WIDTH = 1280, FB_HEIGHT = 720 };
static FojCollGrid g_map;

static void make_synthetic_map(FojCollGrid *grid) {
    grid->width = 50;
    grid->height = 50;
    grid->origin[0] = -250.0f;
    grid->origin[1] = -250.0f;
    grid->step[0] = grid->step[1] = 10.0f;
    for (int y = 0; y < 50; ++y) {
        for (int x = 0; x < 50; ++x) {
            for (int sample = 0; sample < 4; ++sample) {
                grid->samples[y][x][sample] =
                    (float)((x * 3 + y * 5 + sample * 9) % 70) * 0.4f - 8.0f;
            }
            grid->flags[y][x][0] = (uint8_t)(((x + y) % 11) == 0);
            grid->flags[y][x][1] = (uint8_t)(((x * 3 + y) % 31) == 0);
        }
    }
}

static bool load_local_map(const char *path, FojCollGrid *map) {
    FILE *file = fopen(path, "rb");
    if (!file) return false;
    bool okay = false;
    if (fseek(file, 0, SEEK_END) == 0) {
        long len = ftell(file);
        if (len > 0 && len <= FOJ_COLL_MAX_FILE_BYTES &&
            fseek(file, 0, SEEK_SET) == 0) {
            char *buffer = malloc((size_t)len);
            if (buffer) {
                if (fread(buffer, 1, (size_t)len, file) == (size_t)len)
                    okay = foj_coll_parse(buffer, (size_t)len, map) == FOJ_COLL_OK;
                free(buffer);
            }
        }
    }
    fclose(file);
    return okay;
}

static void status_marker(uint32_t *pixels, int stride, bool authentic_data) {
    /* Green = a user-supplied COLL parsed successfully; red = SYNTHETIC.
     * Presence on SD card does not imply authentic publisher provenance. */
    uint32_t color = authentic_data ? UINT32_C(0xff60c376) : UINT32_C(0xff565ee7);
    for (int y = 16; y < 35; ++y) {
        uint32_t *row = pixels + (size_t)y * (size_t)stride;
        for (int x = FB_WIDTH - 45; x < FB_WIDTH - 18; ++x) row[x] = color;
    }
}

int main(int argc, char **argv) {
    (void)argc;
    (void)argv;

    /* There is no automatic game download or PS3 decryption on the console. */
    const char *map_path = "sdmc:/switch/foj/maps/map1-1.coll";
    /* Some homebrew launchers have already mounted sdmc: before main(). */
    bool loaded = load_local_map(map_path, &g_map);
    if (!loaded && R_SUCCEEDED(fsdevMountSdmc()))
        loaded = load_local_map(map_path, &g_map);
    if (!loaded) make_synthetic_map(&g_map);

    padConfigureInput(1, HidNpadStyleSet_NpadStandard);
    PadState pad;
    padInitializeDefault(&pad);

    Framebuffer fb;
    Result result = framebufferCreate(&fb, nwindowGetDefault(),
                                      FB_WIDTH, FB_HEIGHT,
                                      PIXEL_FORMAT_RGBA_8888, 2);
    if (R_FAILED(result)) return 1;
    result = framebufferMakeLinear(&fb);
    if (R_FAILED(result)) {
        framebufferClose(&fb);
        return 1;
    }

    int cursor_x = g_map.width / 2, cursor_y = g_map.height / 2;
    int channel = 0, tile_size = 12;
    while (appletMainLoop()) {
        padUpdate(&pad);
        u64 down = padGetButtonsDown(&pad);
        if (down & HidNpadButton_Plus) break;
        if (down & HidNpadButton_Left) --cursor_x;
        if (down & HidNpadButton_Right) ++cursor_x;
        if (down & HidNpadButton_Up) --cursor_y;
        if (down & HidNpadButton_Down) ++cursor_y;
        if (cursor_x < 0) cursor_x = 0;
        if (cursor_y < 0) cursor_y = 0;
        if (cursor_x >= g_map.width) cursor_x = g_map.width - 1;
        if (cursor_y >= g_map.height) cursor_y = g_map.height - 1;

        if (down & HidNpadButton_R) channel = (channel + 1) % 6;
        if (down & HidNpadButton_L) channel = (channel + 5) % 6;
        if (down & HidNpadButton_ZR && tile_size < 30) tile_size += 2;
        if (down & HidNpadButton_ZL && tile_size > 4) tile_size -= 2;

        u32 stride_bytes = 0;
        u32 *pixels = (u32 *)framebufferBegin(&fb, &stride_bytes);
        if (pixels) {
            int stride = (int)(stride_bytes / sizeof(u32));
            foj_coll_render(&g_map, (uint32_t *)pixels, FB_WIDTH, FB_HEIGHT,
                            stride, cursor_x, cursor_y, tile_size, channel);
            status_marker((uint32_t *)pixels, stride, loaded);
        }
        framebufferEnd(&fb);
    }
    framebufferClose(&fb);
    return 0;
}
