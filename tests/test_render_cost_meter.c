/* Stage240: portable renderer-time telemetry and negative-control tests. */
#include "render_cost_meter.h"

#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static void check_tick_window(void) {
    FojRenderCostMeter meter;
    foj_render_cost_meter_init(&meter);
    assert(!meter.ready && !meter.saturated && meter.completed_windows == 0);
    assert(!foj_render_cost_meter_record(NULL, 10));
    assert(!foj_render_cost_meter_record(&meter, 0));
    for (unsigned i = 0; i < FOJ_RENDER_COST_WINDOW-1; ++i)
        assert(foj_render_cost_meter_record(&meter, 40000));
    assert(!meter.ready && meter.pending_samples == 31);
    assert(foj_render_cost_meter_record(&meter, 40000));
    assert(meter.ready && meter.mean_us == 40 && !meter.saturated);
    assert(meter.completed_windows == 1 && meter.pending_samples == 0);
    for (unsigned i = 0; i < FOJ_RENDER_COST_WINDOW; ++i)
        assert(foj_render_cost_meter_record(&meter, 120000));
    assert(meter.mean_us == 120 && meter.completed_windows == 2);
    for (unsigned i = 0; i < FOJ_RENDER_COST_WINDOW; ++i)
        assert(foj_render_cost_meter_record(&meter, 70000000));
    assert(meter.mean_us == FOJ_RENDER_COST_MAX_US && meter.saturated);
    assert(meter.completed_windows == 3);
}

static void check_overflow_and_fail_closed(void) {
    FojRenderCostMeter meter;
    foj_render_cost_meter_init(&meter);
    assert(foj_render_cost_meter_record(&meter, UINT64_MAX));
    const FojRenderCostMeter before = meter;
    assert(!foj_render_cost_meter_record(&meter, 1));
    assert(memcmp(&meter, &before, sizeof(meter)) == 0);
}

static void check_raster_bounds_and_binary_code(void) {
    enum { W = 512, H = 48 };
    const uint32_t blank = UINT32_C(0xffa1a1a1);
    uint32_t *pixels = malloc((size_t)W * H * sizeof(*pixels));
    assert(pixels);
    FojRenderCostMeter meter;
    foj_render_cost_meter_init(&meter);
    for (int i=0; i<W*H; ++i) pixels[i]=blank;
    assert(!foj_render_cost_meter_draw(NULL,pixels,W,H,W));
    assert(!foj_render_cost_meter_draw(&meter,NULL,W,H,W));
    assert(!foj_render_cost_meter_draw(&meter,pixels,495,H,W));
    assert(!foj_render_cost_meter_draw(&meter,pixels,W,19,W));
    assert(!foj_render_cost_meter_draw(&meter,pixels,W,H,W-1));

    assert(foj_render_cost_meter_draw(&meter,pixels,W,H,W));
    const uint32_t pending = pixels[FOJ_RENDER_COST_Y*W+FOJ_RENDER_COST_X];
    assert(pending != blank);
    assert(pixels[FOJ_RENDER_COST_Y*W+FOJ_RENDER_COST_X-1] == blank);
    assert(pixels[FOJ_RENDER_COST_Y*W+FOJ_RENDER_COST_X+64] == blank);
    for (int i=0; i<32; ++i)
        assert(foj_render_cost_meter_record(&meter, 40000));
    assert(foj_render_cost_meter_draw(&meter,pixels,W,H,W));
    const uint32_t on = pixels[FOJ_RENDER_COST_Y*W+
        FOJ_RENDER_COST_X+FOJ_RENDER_COST_STEP*3];
    const uint32_t off = pixels[FOJ_RENDER_COST_Y*W+
        FOJ_RENDER_COST_X+FOJ_RENDER_COST_STEP*0];
    assert(on != off && off != pending && on != pending);
    for (int bit=0; bit<16; ++bit) {
        const uint32_t sample=pixels[FOJ_RENDER_COST_Y*W+
            FOJ_RENDER_COST_X+FOJ_RENDER_COST_STEP*bit];
        assert(sample == ((40u & (1u << bit)) ? on : off));
    }
    /* Inter-bit gap and pixels beyond the diagnostic remain unchanged. */
    assert(pixels[FOJ_RENDER_COST_Y*W+
        FOJ_RENDER_COST_X+FOJ_RENDER_COST_BAR_WIDTH] == blank);
    assert(pixels[(FOJ_RENDER_COST_Y+8)*W+FOJ_RENDER_COST_X] == blank);
    free(pixels);
}

int main(void) {
    check_tick_window();
    check_overflow_and_fail_closed();
    check_raster_bounds_and_binary_code();
    puts("Stage240 synthetic render timing: stable 32-frame means and pixels OK");
    return 0;
}
