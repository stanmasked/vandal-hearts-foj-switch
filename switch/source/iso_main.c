/*
 * Original, asset-free isometric GPU-independent software-rendering prototype.
 * This is NOT Vandal Hearts: Flames of Judgment's PS3 renderer or game engine.
 */
#include <switch.h>
#include <switch/arm/counter.h>
#include <stdint.h>

#include "tactical_demo.h"
#include "isometric_demo.h"
#include "battle_replay.h"
#include "battle_replay_meter.h"
#include "render_cost_meter.h"
#include "coll_battle_overlay.h"
#include "local_coll_window.h"

#ifndef FOJ_STAGE244_PAIRED_PROBE
#define FOJ_STAGE244_PAIRED_PROBE 0
#endif
#if FOJ_STAGE244_PAIRED_PROBE != 0 && FOJ_STAGE244_PAIRED_PROBE != 1
#error "Stage244 must use 0 or 1 for its research-only diagnostic"
#endif
#if FOJ_STAGE244_PAIRED_PROBE
#include "threat_pair_probe.h"
static uint64_t foj_stage244_guest_now_ns(void *unused) {
    (void)unused;
    return armTicksToNs(armGetSystemTick());
}
#endif

/* Stage243: experimental compare-only switch. Production/default NRO keeps
 * the Stage237 cache. No battle logic, replay or predicted result differs. */
#ifndef FOJ_STAGE243_DISABLE_CACHE
#define FOJ_STAGE243_DISABLE_CACHE 0
#endif
#if FOJ_STAGE243_DISABLE_CACHE != 0 && FOJ_STAGE243_DISABLE_CACHE != 1
#error "Stage243 cache toggle must be 0 or 1"
#endif

enum { FB_WIDTH = 1280, FB_HEIGHT = 720 };
/* Cache telemetry must not overwrite the Stage229 replay input meter.
 * 128 columns start at FOJ_REPLAY_METER_X, covering [256,384). */
enum { FOJ_CACHE_TILE_SIZE = 8, FOJ_CACHE_GEN_X = 400,
       FOJ_CACHE_HITS_X = 412, FOJ_CACHE_TILE_Y = 12 };
_Static_assert(FOJ_CACHE_GEN_X >= FOJ_REPLAY_METER_X + FOJ_REPLAY_MAX_INPUTS,
               "Stage238 cache telemetry overlaps replay input history");
_Static_assert(FOJ_CACHE_HITS_X >= FOJ_CACHE_GEN_X + FOJ_CACHE_TILE_SIZE,
               "Stage238 telemetry squares overlap each other");
_Static_assert(FOJ_CACHE_HITS_X + FOJ_CACHE_TILE_SIZE <= FB_WIDTH,
               "Stage238 telemetry exceeds the framebuffer");
_Static_assert(FOJ_RENDER_COST_X >= FOJ_CACHE_HITS_X + FOJ_CACHE_TILE_SIZE,
               "Stage240 timing pixels overlap Stage238 cache audit");
_Static_assert(FOJ_RENDER_COST_X + FOJ_RENDER_COST_BITS * FOJ_RENDER_COST_STEP <= FB_WIDTH,
               "Stage240 timing pixels leave framebuffer");
/* Stage243: A/B provenance tile must not overwrite the 16 timer bits. */
enum { FOJ_PAIR_MODE_X = 508, FOJ_PAIR_MODE_Y = 12,
       FOJ_PAIR_MODE_SIZE = 8 };
_Static_assert(FOJ_PAIR_MODE_X >= FOJ_RENDER_COST_X +
               FOJ_RENDER_COST_BITS * FOJ_RENDER_COST_STEP,
               "Stage243 experimental build identity overlaps render timer");

#if FOJ_STAGE244_PAIRED_PROBE
_Static_assert(FOJ_PAIR_PROBE_CACHED_X > FOJ_PAIR_MODE_X + FOJ_PAIR_MODE_SIZE,
               "Stage244 paired timing bars overlap Stage243 mode tile");
_Static_assert(FOJ_PAIR_PROBE_UNCACHED_X >= FOJ_PAIR_PROBE_CACHED_X+
               FOJ_PAIR_PROBE_BITS*FOJ_PAIR_PROBE_STEP,
               "Stage244 cached and uncached bars overlap");
_Static_assert(FOJ_PAIR_PROBE_STATUS_X >= FOJ_PAIR_PROBE_UNCACHED_X+
               FOJ_PAIR_PROBE_BITS*FOJ_PAIR_PROBE_STEP,
               "Stage244 pairing status overlaps uncached nanosecond bits");
_Static_assert(FOJ_PAIR_PROBE_STATUS_X+8 <= FB_WIDTH,
               "Stage244 diagnostic leaves the framebuffer");
#endif

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
    bool show_threat_preview=true;

    FojBattle battle;
    foj_battle_init(&battle);
    FojBattleThreatCache threat_cache;
    foj_battle_threat_cache_init(&threat_cache);
    FojRenderCostMeter render_cost;
    foj_render_cost_meter_init(&render_cost);
#if FOJ_STAGE244_PAIRED_PROBE
    FojThreatPairProbe within_guest_probe;
    foj_threat_pair_probe_init(&within_guest_probe);
#endif
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
        /* Right-stick click toggles only presentation, not battle inputs. */
        if (pressed & HidNpadButton_StickR)
            show_threat_preview=!show_threat_preview;

        u32 stride_bytes = 0;
        u32 *pixels = (u32 *)framebufferBegin(&framebuffer, &stride_bytes);
        if (pixels) {
            /* libnx's AArch64 system counter measures only CPU-side
             * software battle rendering, excluding buffer acquire/present,
             * COLL overlay and HUD telemetry. No emulated FPS assertion. */
            const u64 render_start_tick = armGetSystemTick();
            foj_iso_render_battle_cached_options(&battle, (uint32_t *)pixels,
                FB_WIDTH, FB_HEIGHT,
                (int)(stride_bytes / sizeof(u32)),show_threat_preview,
                FOJ_STAGE243_DISABLE_CACHE ? NULL : &threat_cache);
            const u64 render_elapsed_ticks = armGetSystemTick() - render_start_tick;
            (void)foj_render_cost_meter_record(
                &render_cost, armTicksToNs(render_elapsed_ticks));
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
            (void)foj_replay_render_meter(&replay, (uint32_t *)pixels,
                                          FB_WIDTH, FB_HEIGHT, pixel_stride);
            for (int iy=12;iy<20;++iy)
                for (int ix=240;ix<248;++ix)
                    pixels[iy*pixel_stride+ix] = audit_color;
            /* Stage238: guest-visible, noninteractive cache diagnostics.
             * Left 8x8: gray=invalid, cyan=first matrix calculation,
             * gold=second, magenta=unexpected further recalculations.
             * Right 8x8: mint=at least one genuine cache hit; violet=no hits.
             * This is display-only: no tactical input reads these tiles.
             * Distinct colors avoid the Stage223-235 evidence palettes. */
            const u32 cache_generation_color = !threat_cache.valid ?
                0xff685c52u : threat_cache.calculations == 1u ?
                0xffdccb29u : threat_cache.calculations == 2u ?
                0xff40b2e7u : 0xffbe47e5u;
            const u32 cache_hit_color = threat_cache.hits > 0u ?
                0xff88df34u : 0xffc42472u;
            for (int iy=FOJ_CACHE_TILE_Y;
                     iy<FOJ_CACHE_TILE_Y+FOJ_CACHE_TILE_SIZE;++iy) {
                for (int ix=FOJ_CACHE_GEN_X;
                         ix<FOJ_CACHE_GEN_X+FOJ_CACHE_TILE_SIZE;++ix)
                    pixels[iy*pixel_stride+ix] = cache_generation_color;
                for (int ix=FOJ_CACHE_HITS_X;
                         ix<FOJ_CACHE_HITS_X+FOJ_CACHE_TILE_SIZE;++ix)
                    pixels[iy*pixel_stride+ix] = cache_hit_color;
            }
            /* Stage240: 16 bit, low bit first, software-render mean
             * microseconds across 32 frames. Draw after original overlays
             * and outside all previous diagnostic color neighborhoods. */
            (void)foj_render_cost_meter_draw(&render_cost,
                (uint32_t *)pixels,FB_WIDTH,FB_HEIGHT,pixel_stride);
#if FOJ_STAGE244_PAIRED_PROBE
            /* Research-only, no gameplay mutation: compare a warm-cache
             * forecast call with its uncached counterpart inside the same
             * AArch64 process, in alternating AB/BA order. The independent
             * probe cache is never the cache used by the real renderer. */
            (void)foj_threat_pair_probe_step(
                &within_guest_probe,show_threat_preview ? &battle : NULL,
                foj_stage244_guest_now_ns,NULL);
            (void)foj_threat_pair_probe_draw(
                &within_guest_probe, (uint32_t *)pixels,
                FB_WIDTH, FB_HEIGHT,pixel_stride);
#endif
            /* Draw *after* timing so mode identification cannot affect
             * the measured region. Distinct from all earlier HUD colors.
             * RGB: cached=(17,207,241), uncached=(238,94,21). */
            const uint32_t pair_color = FOJ_STAGE243_DISABLE_CACHE ?
                UINT32_C(0xff155eee) : UINT32_C(0xfff1cf11);
            for (int yy=FOJ_PAIR_MODE_Y;
                     yy<FOJ_PAIR_MODE_Y+FOJ_PAIR_MODE_SIZE; ++yy)
                for (int xx=FOJ_PAIR_MODE_X;
                         xx<FOJ_PAIR_MODE_X+FOJ_PAIR_MODE_SIZE; ++xx)
                    pixels[yy*pixel_stride+xx] = pair_color;
        }
        framebufferEnd(&framebuffer);
    }

    framebufferClose(&framebuffer);
    return 0;
}
