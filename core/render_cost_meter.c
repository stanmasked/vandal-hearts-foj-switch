/* Stage240 portable timing accumulator. No Switch time source in core. */
#include "render_cost_meter.h"

#include <stddef.h>
#include <string.h>

enum {
    COLOR_READY_ON = 0xff7fe8ffu,
    COLOR_READY_OFF = 0xff302530u,
    COLOR_PENDING = 0xffb8863fu
};

void foj_render_cost_meter_init(FojRenderCostMeter *meter) {
    if (meter) memset(meter, 0, sizeof(*meter));
}

bool foj_render_cost_meter_record(FojRenderCostMeter *meter,
                                   uint64_t elapsed_ns) {
    if (!meter || elapsed_ns == 0 ||
        elapsed_ns > UINT64_MAX - meter->pending_total_ns ||
        meter->pending_samples >= FOJ_RENDER_COST_WINDOW)
        return false;

    meter->pending_total_ns += elapsed_ns;
    ++meter->pending_samples;
    if (meter->pending_samples == FOJ_RENDER_COST_WINDOW) {
        const uint64_t average_ns =
            meter->pending_total_ns / FOJ_RENDER_COST_WINDOW;
        const uint64_t micros = average_ns / UINT64_C(1000);
        meter->saturated = micros > FOJ_RENDER_COST_MAX_US;
        meter->mean_us = meter->saturated ?
            FOJ_RENDER_COST_MAX_US : (uint32_t)micros;
        meter->ready = true;
        ++meter->completed_windows;
        meter->pending_total_ns = 0;
        meter->pending_samples = 0;
    }
    return true;
}

bool foj_render_cost_meter_draw(const FojRenderCostMeter *meter,
                                uint32_t *pixels,
                                int width, int height, int stride) {
    if (!meter || !pixels || width < FOJ_RENDER_COST_X +
        FOJ_RENDER_COST_BITS * FOJ_RENDER_COST_STEP ||
        height < FOJ_RENDER_COST_Y + FOJ_RENDER_COST_BAR_HEIGHT ||
        stride < width)
        return false;
    for (int bit = 0; bit < FOJ_RENDER_COST_BITS; ++bit) {
        const uint32_t color = !meter->ready ? COLOR_PENDING :
            (meter->mean_us & (UINT32_C(1) << bit)) ?
            COLOR_READY_ON : COLOR_READY_OFF;
        for (int yy = 0; yy < FOJ_RENDER_COST_BAR_HEIGHT; ++yy) {
            for (int xx = 0; xx < FOJ_RENDER_COST_BAR_WIDTH; ++xx) {
                const size_t offset =
                    (size_t)(FOJ_RENDER_COST_Y + yy) * (size_t)stride +
                    (size_t)(FOJ_RENDER_COST_X +
                             bit * FOJ_RENDER_COST_STEP + xx);
                pixels[offset] = color;
            }
        }
    }
    return true;
}
