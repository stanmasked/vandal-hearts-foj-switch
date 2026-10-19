/* Stage246 generated-only phase partition regressions: no GPU, no FPS. */
#include "isometric_demo.h"
#include "isometric_phase_meter.h"
#include <assert.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>

enum { W=320, H=180 };
typedef struct { uint64_t tick, step; unsigned calls; } Clock;
static uint64_t monotonic(void *opaque) {
    Clock *c=(Clock *)opaque;
    ++c->calls;
    c->tick+=c->step;
    return c->tick;
}
static uint64_t frozen(void *opaque) {
    Clock *c=(Clock *)opaque;
    ++c->calls;
    return 7;
}
static uint64_t one_tick_quantized(void *opaque) {
    /* AArch64 system clock may quantize a skipped conditional block
     * to zero elapsed ticks. Whole raster must still have advanced. */
    Clock *c=(Clock *)opaque;
    const uint64_t stamps[5]={100,200,200,200,400};
    assert(c->calls<5);
    return stamps[c->calls++];
}
static uint64_t reversed_tick(void *opaque) {
    Clock *c=(Clock *)opaque;
    const uint64_t stamps[5]={100,300,299,400,500};
    assert(c->calls<5);
    return stamps[c->calls++];
}

static uint32_t *image(void) {
    uint32_t *pixels=calloc((size_t)W*H,sizeof(uint32_t));
    assert(pixels);
    return pixels;
}

static void verify_scene(bool selected,bool show) {
    FojBattle battle,original;
    foj_battle_init(&battle);
    if (selected) assert(foj_battle_confirm(&battle)==FOJ_BATTLE_SELECTED);
    original=battle;
    uint32_t *profiled=image(),*normal=image();
    FojBattleThreatCache cache_a,cache_b;
    foj_battle_threat_cache_init(&cache_a);
    foj_battle_threat_cache_init(&cache_b);
    Clock clock={0,UINT64_C(1000000),0};
    FojIsoPhaseReceipt receipt;
    foj_iso_render_battle_profiled(&battle,profiled,W,H,W,show,&cache_a,
                                   monotonic,&clock,&receipt);
    foj_iso_render_battle_cached_options(&battle,normal,W,H,W,show,&cache_b);
    assert(!memcmp(profiled,normal,sizeof(uint32_t)*(size_t)W*H));
    assert(!memcmp(&battle,&original,sizeof(battle)));
    assert(receipt.valid && clock.calls==5);
    assert(receipt.terrain_ns==UINT64_C(1000000));
    assert(receipt.threat_compute_ns==UINT64_C(1000000));
    assert(receipt.threat_paint_ns==UINT64_C(1000000));
    assert(receipt.battle_hud_ns==UINT64_C(1000000));
    assert(receipt.whole_raster_ns==UINT64_C(4000000));
    assert(receipt.forecast_available==(selected && show));
    free(profiled);free(normal);
}

static void bad_clock_and_no_extra_production_ticks(void) {
    FojBattle battle;
    foj_battle_init(&battle);
    uint32_t *pixels=image();
    FojIsoPhaseReceipt receipt;
    Clock clock={0,1000,0};
    foj_iso_render_battle_profiled(&battle,pixels,W,H,W,true,NULL,
                                   frozen,&clock,&receipt);
    assert(!receipt.valid && clock.calls==5);
    foj_iso_render_battle_profiled(&battle,pixels,W,H,W,true,NULL,
                                   monotonic,&clock,NULL);
    assert(clock.calls==5); /* receipt disabled, clock not consulted */
    foj_iso_render_battle_profiled(&battle,pixels,W,H,W,true,NULL,
                                   NULL,NULL,&receipt);
    assert(!receipt.valid);
    free(pixels);
}

static void quantized_subphase_is_not_clock_failure(void) {
    FojBattle battle;
    foj_battle_init(&battle);
    uint32_t *pixels=image();
    Clock clock={0,0,0};
    FojIsoPhaseReceipt receipt;
    foj_iso_render_battle_profiled(&battle,pixels,W,H,W,false,NULL,
                                   one_tick_quantized,&clock,&receipt);
    assert(receipt.valid && clock.calls==5);
    assert(receipt.terrain_ns==100);
    assert(receipt.threat_compute_ns==0);
    assert(receipt.threat_paint_ns==0);
    assert(receipt.battle_hud_ns==200);
    assert(receipt.whole_raster_ns==300);
    clock.calls=0;
    foj_iso_render_battle_profiled(&battle,pixels,W,H,W,false,NULL,
                                   reversed_tick,&clock,&receipt);
    assert(!receipt.valid && clock.calls==5);
    free(pixels);
}

static FojIsoPhaseReceipt fake(uint64_t step) {
    FojIsoPhaseReceipt p={0};
    p.terrain_ns=step;
    p.threat_compute_ns=step;
    p.threat_paint_ns=step;
    p.battle_hud_ns=step;
    p.whole_raster_ns=step*4;
    p.forecast_available=true;
    p.valid=true;
    return p;
}
static void meter_window_and_pixel_contract(void) {
    FojIsoPhaseMeter meter;
    foj_iso_phase_meter_init(&meter);
    FojIsoPhaseReceipt p=fake(1234000);
    for(int i=0;i<FOJ_PHASE_METER_WINDOW;++i)
        assert(foj_iso_phase_meter_record(&meter,&p));
    assert(meter.ready && !meter.failed && meter.completed_windows==1u);
    assert(meter.frame_count==0);
    assert(meter.terrain_mean_us==1234 && meter.forecast_mean_us==1234);
    assert(meter.markers_mean_us==1234 && meter.hud_mean_us==1234);
    const int sw=1246, sh=20;
    uint32_t *pixels=calloc((size_t)sw*sh,sizeof(uint32_t));
    assert(pixels);
    assert(foj_iso_phase_meter_draw(&meter,pixels,sw,sh,sw));
    assert(pixels[FOJ_PHASE_METER_Y*sw+FOJ_PHASE_METER_STATUS_X]==
           UINT32_C(0xff84e65a));
    /* 1234 decimal contains bit 1. */
    assert(pixels[FOJ_PHASE_METER_Y*sw+FOJ_PHASE_METER_TERRAIN_X+4]==
           UINT32_C(0xff83d44a));
    assert(pixels[FOJ_PHASE_METER_Y*sw+FOJ_PHASE_METER_FORECAST_X+4]==
           UINT32_C(0xff4265eb));
    assert(pixels[FOJ_PHASE_METER_Y*sw+FOJ_PHASE_METER_MARKERS_X+4]==
           UINT32_C(0xff51bbde));
    assert(pixels[FOJ_PHASE_METER_Y*sw+FOJ_PHASE_METER_HUD_X+4]==
           UINT32_C(0xffef7f9a));
    assert(!foj_iso_phase_meter_draw(&meter,pixels,1245,sh,sw));
    assert(!foj_iso_phase_meter_draw(&meter,pixels,sw,19,sw));
    assert(!foj_iso_phase_meter_draw(&meter,pixels,sw,sh,sw-1));
    assert(!foj_iso_phase_meter_draw(NULL,pixels,sw,sh,sw));
    assert(!foj_iso_phase_meter_draw(&meter,NULL,sw,sh,sw));
    free(pixels);
}
static void meter_rejects_incomplete_or_forged_receipts(void) {
    FojIsoPhaseMeter meter;
    foj_iso_phase_meter_init(&meter);
    FojIsoPhaseReceipt p=fake(1000);
    p.valid=false;
    assert(!foj_iso_phase_meter_record(&meter,&p) && meter.failed);
    foj_iso_phase_meter_init(&meter);
    p=fake(1000);
    p.whole_raster_ns=5000; /* impossible exclusive partition */
    assert(!foj_iso_phase_meter_record(&meter,&p) && meter.failed);
    foj_iso_phase_meter_init(&meter);
    p=fake(UINT64_C(65535000));
    for(int i=0;i<FOJ_PHASE_METER_WINDOW-1;++i)
        assert(foj_iso_phase_meter_record(&meter,&p));
    assert(!foj_iso_phase_meter_record(&meter,&p) && meter.failed);
    foj_iso_phase_meter_init(&meter);
    p=fake(1000);
    p.terrain_ns=UINT64_MAX;
    assert(!foj_iso_phase_meter_record(&meter,&p) && meter.failed);
    assert(!foj_iso_phase_meter_record(NULL,&p));
    assert(!foj_iso_phase_meter_record(&meter,NULL));
}
int main(void) {
    verify_scene(false,true);
    verify_scene(true,true);
    verify_scene(true,false);
    bad_clock_and_no_extra_production_ticks();
    quantized_subphase_is_not_clock_failure();
    meter_window_and_pixel_contract();
    meter_rejects_incomplete_or_forged_receipts();
    return EXIT_SUCCESS;
}
