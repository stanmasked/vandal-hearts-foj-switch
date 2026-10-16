/*
 * Original, asset-free isometric GPU-independent software-rendering prototype.
 * This is NOT Vandal Hearts: Flames of Judgment's PS3 renderer or game engine.
 */
#include <switch.h>
#include <stdint.h>

#include "tactical_demo.h"
#include "isometric_demo.h"

enum { FB_WIDTH = 1280, FB_HEIGHT = 720 };

int main(int argc, char **argv) {
    (void)argc;
    (void)argv;

    padConfigureInput(1, HidNpadStyleSet_NpadStandard);
    PadState pad;
    padInitializeDefault(&pad);

    Framebuffer framebuffer;
    Result rc = framebufferCreate(&framebuffer, nwindowGetDefault(),
                                  FB_WIDTH, FB_HEIGHT,
                                  PIXEL_FORMAT_RGBA_8888, 2);
    if (R_FAILED(rc)) return 1;
    rc = framebufferMakeLinear(&framebuffer);
    if (R_FAILED(rc)) {
        framebufferClose(&framebuffer);
        return 1;
    }

    FojDemo state;
    foj_demo_init(&state);
    while (appletMainLoop()) {
        padUpdate(&pad);
        const u64 pressed = padGetButtonsDown(&pad);

        if (pressed & HidNpadButton_Plus) break;
        if (pressed & HidNpadButton_Up) foj_move_cursor(&state, 0, -1);
        if (pressed & HidNpadButton_Down) foj_move_cursor(&state, 0, 1);
        if (pressed & HidNpadButton_Left) foj_move_cursor(&state, -1, 0);
        if (pressed & HidNpadButton_Right) foj_move_cursor(&state, 1, 0);
        if (pressed & HidNpadButton_A) (void)foj_press_a(&state);
        if (pressed & HidNpadButton_B) (void)foj_press_b(&state);

        u32 stride_bytes = 0;
        u32 *pixels = (u32 *)framebufferBegin(&framebuffer, &stride_bytes);
        if (pixels) {
            foj_iso_render(&state, (uint32_t *)pixels, FB_WIDTH, FB_HEIGHT,
                           (int)(stride_bytes / sizeof(u32)));
        }
        framebufferEnd(&framebuffer);
    }

    framebufferClose(&framebuffer);
    return 0;
}
