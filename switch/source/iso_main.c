/*
 * Original, asset-free isometric GPU-independent software-rendering prototype.
 * This is NOT Vandal Hearts: Flames of Judgment's PS3 renderer or game engine.
 */
#include <switch.h>
#include <stdint.h>

#include "tactical_demo.h"
#include "isometric_demo.h"
#include "battle_replay.h"
#include "coll_battle_overlay.h"
#include "local_coll_window.h"

enum { FB_WIDTH = 1280, FB_HEIGHT = 720 };

static FojCollBattleWindow raw_window;

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

    const char *local_path = "sdmc:/switch/foj/maps/map1-1.coll";
    bool raw_loaded=foj_local_coll_load_path(local_path,&raw_window);
    if (!raw_loaded && R_SUCCEEDED(fsdevMountSdmc()))
        raw_loaded=foj_local_coll_load_path(local_path,&raw_window);
    unsigned raw_channel=0;
    bool show_raw_window=true;

    FojBattle battle;
    foj_battle_init(&battle);
    FojBattleReplay replay;
    foj_replay_init(&replay);
    bool replay_ok = true;
    while (appletMainLoop()) {
        padUpdate(&pad);
        const u64 pressed = padGetButtonsDown(&pad);

        if (pressed & HidNpadButton_Plus) break;
        bool battle_input = false;
        if (pressed & HidNpadButton_Up) {
            (void)foj_replay_record(&replay,&battle,FOJ_REPLAY_UP,NULL);
            battle_input = true;
        }
        if (pressed & HidNpadButton_Down) {
            (void)foj_replay_record(&replay,&battle,FOJ_REPLAY_DOWN,NULL);
            battle_input = true;
        }
        if (pressed & HidNpadButton_Left) {
            (void)foj_replay_record(&replay,&battle,FOJ_REPLAY_LEFT,NULL);
            battle_input = true;
        }
        if (pressed & HidNpadButton_Right) {
            (void)foj_replay_record(&replay,&battle,FOJ_REPLAY_RIGHT,NULL);
            battle_input = true;
        }
        if (pressed & HidNpadButton_A) {
            (void)foj_replay_record(&replay,&battle,FOJ_REPLAY_A,NULL);
            battle_input = true;
        }
        if (pressed & HidNpadButton_B) {
            (void)foj_replay_record(&replay,&battle,FOJ_REPLAY_B,NULL);
            battle_input = true;
        }
        if (pressed & HidNpadButton_X) {
            (void)foj_replay_record(&replay,&battle,FOJ_REPLAY_X,NULL);
            battle_input = true;
        }
        if (pressed & HidNpadButton_ZR) {
            (void)foj_replay_record(&replay,&battle,FOJ_REPLAY_ZR,NULL);
            battle_input = true;
        }
        if (pressed & HidNpadButton_Y) {
            (void)foj_replay_record(&replay,&battle,FOJ_REPLAY_Y,NULL);
            battle_input = true;
        }
        if (pressed & HidNpadButton_Minus) {
            (void)foj_replay_record(&replay,&battle,FOJ_REPLAY_RESET,NULL);
            battle_input = true;
        }
        if (battle_input) replay_ok = foj_replay_matches(&replay,&battle);
        /* Only change diagnostic presentation, never combat/pathfinding. */
        if (pressed & HidNpadButton_L) raw_channel=(raw_channel+5u)%6u;
        if (pressed & HidNpadButton_R) raw_channel=(raw_channel+1u)%6u;
        if (pressed & HidNpadButton_ZL) show_raw_window=!show_raw_window;

        u32 stride_bytes = 0;
        u32 *pixels = (u32 *)framebufferBegin(&framebuffer, &stride_bytes);
        if (pixels) {
            foj_iso_render_battle(&battle, (uint32_t *)pixels, FB_WIDTH, FB_HEIGHT,
                           (int)(stride_bytes / sizeof(u32)));
            if (raw_loaded && show_raw_window)
                (void)foj_coll_battle_overlay(
                    &raw_window,(uint32_t *)pixels,FB_WIDTH,FB_HEIGHT,
                    (int)(stride_bytes / sizeof(u32)),
                    battle.map.cursor_x,battle.map.cursor_y,raw_channel);
            /* 8x8 guest-only audit indicator. Green = replay identical,
             * red = mismatch, amber = input log reached safe capacity.
             * Never interferes with synthetic battle state or COLL values. */
            /* Unique colors, disjoint from hero, guard, enemy and win
             * evidence palettes used by Stage223–227 guest classifiers. */
            const u32 audit_color = !replay_ok ? 0xff3838ffu :
                replay.count >= FOJ_REPLAY_MAX_INPUTS ?
                    0xff2ab6ffu : 0xff44e630u;
            const int pixel_stride = (int)(stride_bytes / sizeof(u32));
            for (int iy=12;iy<20;++iy)
                for (int ix=12;ix<20;++ix)
                    pixels[iy*pixel_stride+ix] = audit_color;
        }
        framebufferEnd(&framebuffer);
    }

    framebufferClose(&framebuffer);
    return 0;
}
