#ifndef FOJ_RENDER_COST_METER_H
#define FOJ_RENDER_COST_METER_H

/* Stage240: self-contained, generated-only screen-space diagnostic meter.
 * The caller chooses the clock. This module measures no GPU/present/FPS.
 * Wait for 32 valid samples, then display their mean render microseconds.
 */
#include <stdbool.h>
#include <stdint.h>

enum {
    FOJ_RENDER_COST_WINDOW = 32,
    FOJ_RENDER_COST_X = 432,
    FOJ_RENDER_COST_Y = 12,
    FOJ_RENDER_COST_BITS = 16,
    FOJ_RENDER_COST_STEP = 4,
    FOJ_RENDER_COST_BAR_WIDTH = 3,
    FOJ_RENDER_COST_BAR_HEIGHT = 8,
    FOJ_RENDER_COST_MAX_US = 65535
};

typedef struct {
    uint64_t pending_total_ns;
    uint32_t pending_samples;
    uint32_t mean_us;
    uint64_t completed_windows;
    bool ready;
    bool saturated;
} FojRenderCostMeter;

void foj_render_cost_meter_init(FojRenderCostMeter *meter);
/* Elapsed nanoseconds of the software renderer only.
 * Returns false for invalid samples / impossible additions. */
bool foj_render_cost_meter_record(FojRenderCostMeter *meter,
                                   uint64_t elapsed_ns);
/* Draw 16 least significant bits, low bit first. When not ready, draws a
 * third "not measured" color rather than inventing a numeric value.
 * Bit value is saturated to 65535 us when necessary. */
bool foj_render_cost_meter_draw(const FojRenderCostMeter *meter,
                                uint32_t *pixels,
                                int width, int height, int stride);

#endif
