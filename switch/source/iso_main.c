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

#ifndef FOJ_STAGE246_PHASE_TIMING
#define FOJ_STAGE246_PHASE_TIMING 0
#endif
#if FOJ_STAGE246_PHASE_TIMING != 0 && FOJ_STAGE246_PHASE_TIMING != 1
#error "Stage246 profile switch must be 0 or 1"
#endif
#if FOJ_STAGE246_PHASE_TIMING
#include "isometric_phase_meter.h"
static uint64_t foj_stage246_now_ns(void *ctx) {
    (void)ctx;
    return armTicksToNs(armGetSystemTick());
}
#endif

#ifndef FOJ_STAGE247_BASE_CACHE
#define FOJ_STAGE247_BASE_CACHE 0
#endif
#if FOJ_STAGE247_BASE_CACHE != 0 && FOJ_STAGE247_BASE_CACHE != 1
#error "Stage247 base-cache mode must be 0 or 1"
#endif
#if FOJ_STAGE247_BASE_CACHE && !FOJ_STAGE246_PHASE_TIMING
#error "Stage247 guest requires the Stage246 phase timing decoder"
#endif
#if FOJ_STAGE247_BASE_CACHE
/* ~3.52 MiB research storage kept outside small Switch thread stacks. */
static FojIsoBaseCache stage247_base_cache;
enum { FOJ_STAGE247_STATUS_X=1252, FOJ_STAGE247_STATUS_Y=12 };
#endif

#ifndef FOJ_STAGE248_BASE_PAIRS
#define FOJ_STAGE248_BASE_PAIRS 0
#endif
#if FOJ_STAGE248_BASE_PAIRS != 0 && FOJ_STAGE248_BASE_PAIRS != 1
#error "Stage248 base-cache paired diagnostic must be 0 or 1"
#endif
#if FOJ_STAGE248_BASE_PAIRS && (!FOJ_STAGE247_BASE_CACHE || !FOJ_STAGE246_PHASE_TIMING)
#error "Stage248 guest requires Stage247 and Stage246 measurement paths"
#endif
#ifndef FOJ_STAGE249_STABILITY
#define FOJ_STAGE249_STABILITY 0
#endif
#if FOJ_STAGE249_STABILITY != 0 && FOJ_STAGE249_STABILITY != 1
#error "Stage249 stability diagnostic must be 0 or 1"
#endif
#if FOJ_STAGE249_STABILITY && !FOJ_STAGE248_BASE_PAIRS
#error "Stage249 requires in-process Stage248 parity probe"
#endif
#ifndef FOJ_STAGE250_SCALE
#define FOJ_STAGE250_SCALE 0
#endif
#if FOJ_STAGE250_SCALE != 0 && FOJ_STAGE250_SCALE != 1
#error "Stage250 scale diagnostic must be 0 or 1"
#endif
#if FOJ_STAGE250_SCALE && !FOJ_STAGE249_STABILITY
#error "Stage250 scale probe requires Stage249 stable measurement guest"
#endif
#ifndef FOJ_STAGE251_COMPACT
#define FOJ_STAGE251_COMPACT 0
#endif
#if FOJ_STAGE251_COMPACT != 0 && FOJ_STAGE251_COMPACT != 1
#error "Stage251 compact base-cache flag must be 0 or 1"
#endif
#if FOJ_STAGE251_COMPACT && !FOJ_STAGE250_SCALE
#error "Stage251 compact base cache requires Stage250 scaling guest"
#endif
#ifndef FOJ_STAGE252_STRESS
#define FOJ_STAGE252_STRESS 0
#endif
#if FOJ_STAGE252_STRESS != 0 && FOJ_STAGE252_STRESS != 1
#error "Stage252 stress mode requires flag 0 or 1"
#endif
#if FOJ_STAGE252_STRESS && !FOJ_STAGE251_COMPACT
#error "Stage252 requires Stage251 compact research NRO"
#endif
#ifndef FOJ_STAGE253_CHURN
#define FOJ_STAGE253_CHURN 0
#endif
#if FOJ_STAGE253_CHURN != 0 && FOJ_STAGE253_CHURN != 1
#error "Stage253 churn flag must be 0 or 1"
#endif
#if FOJ_STAGE253_CHURN && !FOJ_STAGE252_STRESS
#error "Stage253 requires the isolated Stage252 research guest"
#endif
#ifndef FOJ_STAGE254_REUSE
#define FOJ_STAGE254_REUSE 0
#endif
#if FOJ_STAGE254_REUSE != 0 && FOJ_STAGE254_REUSE != 1
#error "Stage254 bounded reuse flag must be 0 or 1"
#endif
#if FOJ_STAGE254_REUSE && !FOJ_STAGE253_CHURN
#error "Stage254 requires Stage253 research NRO"
#endif
#if FOJ_STAGE254_REUSE
#include "compact_reuse_probe.h"
static FojReuseReceipt stage254_reuse;
#endif
#ifndef FOJ_STAGE255_BUDGET_FALLBACK
#define FOJ_STAGE255_BUDGET_FALLBACK 0
#endif
#if FOJ_STAGE255_BUDGET_FALLBACK != 0 && FOJ_STAGE255_BUDGET_FALLBACK != 1
#error "Stage255 budget fallback flag must be 0 or 1"
#endif
#if FOJ_STAGE255_BUDGET_FALLBACK && !FOJ_STAGE254_REUSE
#error "Stage255 needs Stage254's explicit research-mode cache"
#endif
#if FOJ_STAGE255_BUDGET_FALLBACK
#include "compact_budget_probe.h"
static FojBudgetReceipt stage255_budget;
#endif
#if FOJ_STAGE253_CHURN
#include "compact_churn_probe.h"
static FojCompactChurnReceipt stage253_churn;
#endif
#if FOJ_STAGE252_STRESS
#include "compact_stress_probe.h"
static FojCompactStressReceipt stage252_stress;
#endif
#if FOJ_STAGE250_SCALE
#include "base_cache_scale_probe.h"
static FojBaseScaleProbe stage250_probe;
#endif
#if FOJ_STAGE248_BASE_PAIRS
#include "base_cache_pair_probe.h"
#if FOJ_STAGE249_STABILITY
#include "base_cache_stability_probe.h"
static FojBaseStabilityProbe stage249_probe;
#else
static FojBasePairProbe stage248_probe;
#endif
static uint32_t stage248_cached_pixels[1280*720];
static uint32_t stage248_uncached_pixels[1280*720];
#endif

#ifndef FOJ_STAGE245_RENDER_PAIR
#define FOJ_STAGE245_RENDER_PAIR 0
#endif
#if FOJ_STAGE245_RENDER_PAIR != 0 && FOJ_STAGE245_RENDER_PAIR != 1
#error "Stage245 software-render control must be 0 or 1"
#endif
#if FOJ_STAGE245_RENDER_PAIR
#include "render_pair_probe.h"
static uint64_t foj_stage245_guest_now_ns(void *unused) {
    (void)unused;
    return armTicksToNs(armGetSystemTick());
}
#endif

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

#if FOJ_STAGE247_BASE_CACHE
_Static_assert(FOJ_STAGE247_STATUS_X >= FOJ_PHASE_METER_STATUS_X+8,
               "Stage247 cache hit tile overlaps Stage246 diagnostic status");
_Static_assert(FOJ_STAGE247_STATUS_X+8 <= FB_WIDTH,
               "Stage247 tile exceeds framebuffer");
#endif

#if FOJ_STAGE248_BASE_PAIRS
_Static_assert(FOJ_BASE_PAIR_CACHED_X >= FOJ_PAIR_MODE_X+FOJ_PAIR_MODE_SIZE,
               "Stage248 A/B evidence overlaps build identity");
_Static_assert(FOJ_BASE_PAIR_UNCACHED_X >=
               FOJ_BASE_PAIR_CACHED_X+FOJ_BASE_PAIR_BITS*FOJ_BASE_PAIR_STEP,
               "Stage248 A/B bitfields overlap");
_Static_assert(FOJ_BASE_PAIR_STATUS_X >=
               FOJ_BASE_PAIR_UNCACHED_X+FOJ_BASE_PAIR_BITS*FOJ_BASE_PAIR_STEP,
               "Stage248 parity marker overlaps bitfields");
_Static_assert(FOJ_BASE_PAIR_STATUS_X+8 <= FOJ_PHASE_METER_TERRAIN_X,
               "Stage248 must not overlap Stage246 four-phase diagnostics");
#endif

#if FOJ_STAGE249_STABILITY
_Static_assert(FOJ_BASE_STABILITY_COLD_X >= FOJ_PAIR_MODE_X+FOJ_PAIR_MODE_SIZE,
               "Stage249 refill telemetry overlaps build-mode identity");
_Static_assert(FOJ_BASE_STABILITY_WARM_X >=
    FOJ_BASE_STABILITY_COLD_X+FOJ_BASE_STABILITY_BITS*FOJ_BASE_STABILITY_STEP,
    "Stage249 cold/warm telemetry overlap");
_Static_assert(FOJ_BASE_STABILITY_SPREAD_X >=
    FOJ_BASE_STABILITY_WARM_X+FOJ_BASE_STABILITY_BITS*FOJ_BASE_STABILITY_STEP,
    "Stage249 warm/spread telemetry overlap");
_Static_assert(FOJ_BASE_STABILITY_STATUS_X >=
    FOJ_BASE_STABILITY_SPREAD_X+FOJ_BASE_STABILITY_BITS*FOJ_BASE_STABILITY_STEP,
    "Stage249 spread/status overlap");
_Static_assert(FOJ_BASE_STABILITY_STATUS_X+8 <= FOJ_BASE_PAIR_CACHED_X,
    "Stage249 bars overlap Stage248 paired base-cache bars");
_Static_assert(sizeof(FojBaseStabilityProbe) + sizeof(FojIsoBaseCache) +
    (size_t)2*FB_WIDTH*FB_HEIGHT*sizeof(uint32_t) < (size_t)17*1024*1024,
    "Stage249 opt-in NRO research storage unexpectedly exceeds 17 MiB");
#endif

#if FOJ_STAGE250_SCALE
_Static_assert(FOJ_BASE_SCALE_FIRST_X >= FOJ_PAIR_MODE_X+FOJ_PAIR_MODE_SIZE,
               "Stage250 scaling barcode overlaps build mode tile");
_Static_assert(FOJ_BASE_SCALE_STATUS_X >=
    FOJ_BASE_SCALE_FIRST_X+6*72,
    "Stage250 final barcode overlaps readiness tile");
_Static_assert(FOJ_BASE_SCALE_STATUS_X+8 <= FB_WIDTH,
    "Stage250 scaling receipt exceeds framebuffer");
_Static_assert(sizeof(FojBaseScaleProbe)+sizeof(FojBaseStabilityProbe)+
    sizeof(FojIsoBaseCache)+(size_t)2*FB_WIDTH*FB_HEIGHT*sizeof(uint32_t)
    < (size_t)21*1024*1024,
    "Stage250 opt-in static experimental buffers exceed 21 MiB");
#endif

#if FOJ_STAGE255_BUDGET_FALLBACK
_Static_assert(FOJ_BUDGET_Y>=FOJ_REUSE_Y+8,
               "Stage255 optical receipt overlaps Stage254");
_Static_assert(FOJ_BUDGET_STATUS_X>=FOJ_BUDGET_X+6*72,
               "Stage255 final barcode overlaps readiness");
_Static_assert(FOJ_BUDGET_STATUS_X+8<=FB_WIDTH,
               "Stage255 receipt extends past framebuffer");
#endif
#if FOJ_STAGE254_REUSE
_Static_assert(FOJ_REUSE_Y>=FOJ_CHURN_Y+8,
               "Stage254 optical receipt overlaps Stage253");
_Static_assert(FOJ_REUSE_STATUS_X>=FOJ_REUSE_X+6*72,
               "Stage254 last barcode overlaps readiness");
_Static_assert(FOJ_REUSE_STATUS_X+8<=FB_WIDTH,
               "Stage254 receipt extends past framebuffer");
#endif
#if FOJ_STAGE253_CHURN
_Static_assert(FOJ_CHURN_Y>=FOJ_COMPACT_STRESS_Y+8,
               "Stage253 receipt overlaps Stage252");
_Static_assert(FOJ_CHURN_STATUS_X>=FOJ_CHURN_X+6*72,
               "Stage253 final barcode overlaps readiness");
_Static_assert(FOJ_CHURN_STATUS_X+8<=FB_WIDTH,
               "Stage253 receipt extends outside framebuffer");
#endif
#if FOJ_STAGE252_STRESS
_Static_assert(FOJ_COMPACT_STRESS_Y>=FOJ_BASE_COMPACT_Y+8,
               "Stage252 endurance receipt overlaps Stage251 memory");
_Static_assert(FOJ_COMPACT_STRESS_STATUS_X>=
    FOJ_COMPACT_STRESS_FIRST_X+4*72,
    "Stage252 endurance bars overlap readiness status");
_Static_assert(FOJ_COMPACT_STRESS_STATUS_X+8<=FB_WIDTH,
               "Stage252 endurance status overflows framebuffer");
#endif
#if FOJ_STAGE251_COMPACT
_Static_assert(FOJ_BASE_COMPACT_Y >= FOJ_BASE_SCALE_Y+8,
               "Stage251 memory telemetry overlaps Stage250 timing");
_Static_assert(FOJ_BASE_COMPACT_STATUS_X >=
    FOJ_BASE_COMPACT_X+FOJ_BASE_SCALE_MODES*72,
    "Stage251 memory bars overlap the readiness tile");
_Static_assert(sizeof(FojBaseScaleProbe)<4096,
               "Stage251 compact probe unexpectedly reserves static pixels");
#endif

#if FOJ_STAGE245_RENDER_PAIR
_Static_assert(FOJ_RENDER_PAIR_CACHED_X >= FOJ_PAIR_MODE_X+FOJ_PAIR_MODE_SIZE,
               "Stage245 bar overlaps Stage243 build identity");
_Static_assert(FOJ_RENDER_PAIR_UNCACHED_X >=
               FOJ_RENDER_PAIR_CACHED_X+FOJ_RENDER_PAIR_BITS*FOJ_RENDER_PAIR_BAR_STEP,
               "Stage245 cached/uncached bars overlap");
_Static_assert(FOJ_RENDER_PAIR_STATUS_X >=
               FOJ_RENDER_PAIR_UNCACHED_X+FOJ_RENDER_PAIR_BITS*FOJ_RENDER_PAIR_BAR_STEP,
               "Stage245 status overlaps its barcodes");
_Static_assert(FOJ_RENDER_PAIR_STATUS_X+8 <= FB_WIDTH,
               "Stage245 telemetry exceeds framebuffer");
/* These two private buffers are never passed to the visible game
 * presentation path. They allow byte-identical whole-raster parity. */
static uint32_t foj_stage245_cached_pixels[FB_WIDTH*FB_HEIGHT];
static uint32_t foj_stage245_uncached_pixels[FB_WIDTH*FB_HEIGHT];
#endif

#if FOJ_STAGE246_PHASE_TIMING
_Static_assert(FOJ_PHASE_METER_FORECAST_X >= FOJ_PHASE_METER_TERRAIN_X+
               FOJ_PHASE_METER_BITS*FOJ_PHASE_METER_STEP,
               "Stage246 base and threat timing barcodes overlap");
_Static_assert(FOJ_PHASE_METER_MARKERS_X >= FOJ_PHASE_METER_FORECAST_X+
               FOJ_PHASE_METER_BITS*FOJ_PHASE_METER_STEP,
               "Stage246 threat and marker barcodes overlap");
_Static_assert(FOJ_PHASE_METER_HUD_X >= FOJ_PHASE_METER_MARKERS_X+
               FOJ_PHASE_METER_BITS*FOJ_PHASE_METER_STEP,
               "Stage246 marker and HUD barcodes overlap");
_Static_assert(FOJ_PHASE_METER_STATUS_X >= FOJ_PHASE_METER_HUD_X+
               FOJ_PHASE_METER_BITS*FOJ_PHASE_METER_STEP,
               "Stage246 HUD barcode overlaps status");
_Static_assert(FOJ_PHASE_METER_STATUS_X+8<=FB_WIDTH,
               "Stage246 telemetry exceeds framebuffer");
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
#if FOJ_STAGE247_BASE_CACHE
    foj_iso_base_cache_init(&stage247_base_cache);
#endif
    FojRenderCostMeter render_cost;
    foj_render_cost_meter_init(&render_cost);
#if FOJ_STAGE246_PHASE_TIMING
    FojIsoPhaseMeter phase_meter;
    foj_iso_phase_meter_init(&phase_meter);
#endif
#if FOJ_STAGE248_BASE_PAIRS
#if FOJ_STAGE249_STABILITY
    foj_base_stability_init(&stage249_probe);
#if FOJ_STAGE250_SCALE
    foj_base_scale_init(&stage250_probe);
#endif
#else
    foj_base_pair_init(&stage248_probe);
#endif
#endif
#if FOJ_STAGE245_RENDER_PAIR
    FojRenderPairProbe render_pair_probe;
    foj_render_pair_init(&render_pair_probe);
#endif
#if FOJ_STAGE244_PAIRED_PROBE
    FojThreatPairProbe within_guest_probe;
    foj_threat_pair_probe_init(&within_guest_probe);
#endif
#if FOJ_STAGE252_STRESS
    /* Run a private 96-state stress once, before the visible battle.
     * Reuse existing scratch arrays. No input or frame changes. */
    (void)foj_compact_stress_run(
        &stage252_stress,stage248_cached_pixels,stage248_uncached_pixels);
#endif
#if FOJ_STAGE253_CHURN
    /* Separate 384-frame churn trace, once per guest startup. Reuse the
     * private research buffers, never mutate battle, controls or saves. */
    (void)foj_compact_churn_run(
        &stage253_churn,stage248_cached_pixels,stage248_uncached_pixels);
#endif
#if FOJ_STAGE254_REUSE
    /* Compare a bounded 900-KiB floor against the independent exact-sized
     * Stage253 receipt. Run once, before any visible guest battle action. */
    (void)foj_reuse_probe_run(
        &stage254_reuse,&stage253_churn,
        stage248_cached_pixels,stage248_uncached_pixels);
#endif
#if FOJ_STAGE255_BUDGET_FALLBACK
    /* Strict per-frame budget, 16 small-mode fallbacks in 384 frames.
     * This runs on research-only scratch; never modifies battle state. */
    (void)foj_budget_probe_run(
        &stage255_budget,stage248_cached_pixels,stage248_uncached_pixels);
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
#if FOJ_STAGE246_PHASE_TIMING
        /* A timed window must never mix frames captured from different
         * battle actions or overlay visibility modes. One guest command
         * resets the 32-frame average before the first new render.
         * Other NRO variants have no added work. */
        if (battle_input || (pressed & HidNpadButton_StickR))
            foj_iso_phase_meter_init(&phase_meter);
#endif

        u32 stride_bytes = 0;
        u32 *pixels = (u32 *)framebufferBegin(&framebuffer, &stride_bytes);
        if (pixels) {
            /* libnx's AArch64 system counter measures only CPU-side
             * software battle rendering, excluding buffer acquire/present,
             * COLL overlay and HUD telemetry. No emulated FPS assertion. */
            const u64 render_start_tick = armGetSystemTick();
#if FOJ_STAGE246_PHASE_TIMING
            FojIsoPhaseReceipt phase_receipt;
#if FOJ_STAGE247_BASE_CACHE
            bool stage247_hit=false;
            foj_iso_render_battle_profiled_base_cached(
                &battle, (uint32_t *)pixels, FB_WIDTH, FB_HEIGHT,
                (int)(stride_bytes / sizeof(u32)),show_threat_preview,
                FOJ_STAGE243_DISABLE_CACHE ? NULL : &threat_cache,
                &stage247_base_cache, &stage247_hit,
                foj_stage246_now_ns,NULL,&phase_receipt);
#else
            foj_iso_render_battle_profiled(&battle, (uint32_t *)pixels,
                FB_WIDTH, FB_HEIGHT,
                (int)(stride_bytes / sizeof(u32)),show_threat_preview,
                FOJ_STAGE243_DISABLE_CACHE ? NULL : &threat_cache,
                foj_stage246_now_ns,NULL,&phase_receipt);
#endif
            (void)foj_iso_phase_meter_record(&phase_meter,&phase_receipt);
#else
            foj_iso_render_battle_cached_options(&battle, (uint32_t *)pixels,
                FB_WIDTH, FB_HEIGHT,
                (int)(stride_bytes / sizeof(u32)),show_threat_preview,
                FOJ_STAGE243_DISABLE_CACHE ? NULL : &threat_cache);
#endif
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
#if FOJ_STAGE246_PHASE_TIMING
            /* Only an explicitly compiled research guest emits phase
             * telemetry. All four bars are painted outside the rasterizer
             * timing region; no combat rule or original asset is touched. */
            (void)foj_iso_phase_meter_draw(&phase_meter,
                (uint32_t *)pixels,FB_WIDTH,FB_HEIGHT,pixel_stride);
#if FOJ_STAGE247_BASE_CACHE
            /* Guest-only proof: green if this frame actually reused the
             * scene-exact cached base, red for a cold/new-scene miss.
             * Nothing reads this indicator to decide gameplay actions. */
            const u32 base_color=stage247_hit ?
                UINT32_C(0xff83e72a) : UINT32_C(0xff3131f2);
            for (int y=FOJ_STAGE247_STATUS_Y;y<FOJ_STAGE247_STATUS_Y+8;++y)
                for (int x=FOJ_STAGE247_STATUS_X;
                         x<FOJ_STAGE247_STATUS_X+8;++x)
                    pixels[y*pixel_stride+x]=base_color;
#endif
#endif
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
#if FOJ_STAGE248_BASE_PAIRS
            /* Isolated true A/B: two independently warmed forecast caches,
             * scratch-only full battle rasters, and AB/BA alternating order.
             * Never alter the visible frame or gameplay state. Draw this
             * research-only receipt after both timing regions. */
#if FOJ_STAGE249_STABILITY
#if FOJ_STAGE250_SCALE
            /* Cross-resolution synthetic base sweep runs only once after
             * each state/preview change. Shared private scratch buffers,
             * outside the Stage249 AB/BA raster timing window. */
            (void)foj_base_scale_step(
                &stage250_probe,&battle,show_threat_preview,
                stage248_cached_pixels,stage248_uncached_pixels,
                foj_stage246_now_ns,NULL);
#endif
            (void)foj_base_stability_step(
                &stage249_probe,&battle,show_threat_preview,
                stage248_cached_pixels,stage248_uncached_pixels,
                FB_WIDTH,FB_HEIGHT,FB_WIDTH,foj_stage246_now_ns,NULL);
            (void)foj_base_pair_draw(&stage249_probe.pair,
                (uint32_t *)pixels,FB_WIDTH,FB_HEIGHT,pixel_stride);
            (void)foj_base_stability_draw(&stage249_probe,
                (uint32_t *)pixels,FB_WIDTH,FB_HEIGHT,pixel_stride);
#if FOJ_STAGE250_SCALE
            (void)foj_base_scale_draw(&stage250_probe,
                (uint32_t *)pixels,FB_WIDTH,FB_HEIGHT,pixel_stride);
#if FOJ_STAGE251_COMPACT
            (void)foj_base_scale_draw_memory(&stage250_probe,
                (uint32_t *)pixels,FB_WIDTH,FB_HEIGHT,pixel_stride);
#endif
#if FOJ_STAGE252_STRESS
            (void)foj_compact_stress_draw(&stage252_stress,
                (uint32_t *)pixels,FB_WIDTH,FB_HEIGHT,pixel_stride);
#endif
#if FOJ_STAGE253_CHURN
            (void)foj_compact_churn_draw(&stage253_churn,
                (uint32_t *)pixels,FB_WIDTH,FB_HEIGHT,pixel_stride);
#endif
#if FOJ_STAGE254_REUSE
            (void)foj_reuse_probe_draw(&stage254_reuse,
                (uint32_t *)pixels,FB_WIDTH,FB_HEIGHT,pixel_stride);
#endif
#if FOJ_STAGE255_BUDGET_FALLBACK
            (void)foj_budget_probe_draw(&stage255_budget,
                (uint32_t *)pixels,FB_WIDTH,FB_HEIGHT,pixel_stride);
#endif
#endif
#else
            (void)foj_base_pair_step(
                &stage248_probe,&battle,show_threat_preview,
                stage248_cached_pixels,stage248_uncached_pixels,
                FB_WIDTH,FB_HEIGHT,FB_WIDTH,foj_stage246_now_ns,NULL);
            (void)foj_base_pair_draw(&stage248_probe,(uint32_t *)pixels,
                                     FB_WIDTH,FB_HEIGHT,pixel_stride);
#endif
#endif
#if FOJ_STAGE245_RENDER_PAIR
            /* Two *complete* CPU rasterizations from the same battle
             * state. Only the optional research NRO executes these extra
             * passes. The real framebuffer and production cache cannot
             * be affected; alternate order and check exact pixel parity. */
            (void)foj_render_pair_step(&render_pair_probe,&battle,
                show_threat_preview,foj_stage245_cached_pixels,
                foj_stage245_uncached_pixels,FB_WIDTH,FB_HEIGHT,FB_WIDTH,
                foj_stage245_guest_now_ns,NULL);
            (void)foj_render_pair_draw(&render_pair_probe,
                (uint32_t *)pixels,FB_WIDTH,FB_HEIGHT,pixel_stride);
#endif
        }
        framebufferEnd(&framebuffer);
    }

#if FOJ_STAGE251_COMPACT
    foj_base_scale_release(&stage250_probe);
#endif
    framebufferClose(&framebuffer);
    return 0;
}
