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

    FojBattle battle;
    foj_battle_init(&battle);
    while (appletMainLoop()) {
        padUpdate(&pad);
        const u64 pressed = padGetButtonsDown(&pad);

        if (pressed & HidNpadButton_Plus) break;
        if (pressed & HidNpadButton_Up) foj_battle_move_cursor(&battle, 0, -1);
        if (pressed & HidNpadButton_Down) foj_battle_move_cursor(&battle, 0, 1);
        if (pressed & HidNpadButton_Left) foj_battle_move_cursor(&battle, -1, 0);
        if (pressed & HidNpadButton_Right) foj_battle_move_cursor(&battle, 1, 0);
        if (pressed & HidNpadButton_A) (void)foj_battle_confirm(&battle);
        if (pressed & HidNpadButton_B) (void)foj_battle_cancel(&battle);

        if (pressed & HidNpadButton_X) (void)foj_battle_attack(&battle);
        if (pressed & HidNpadButton_ZR) (void)foj_battle_guard(&battle);
        if (pressed & HidNpadButton_Y) (void)foj_battle_end_turn(&battle);
        if (pressed & HidNpadButton_Minus) foj_battle_init(&battle);

        u32 stride_bytes = 0;
        u32 *pixels = (u32 *)framebufferBegin(&framebuffer, &stride_bytes);
        if (pixels) {
            foj_iso_render_battle(&battle, (uint32_t *)pixels, FB_WIDTH, FB_HEIGHT,
                           (int)(stride_bytes / sizeof(u32)));
        }
        framebufferEnd(&framebuffer);
    }

    framebufferClose(&framebuffer);
    return 0;
}
