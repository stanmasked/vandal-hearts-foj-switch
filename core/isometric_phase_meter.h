#ifndef FOJ_STAGE246_PHASE_METER_H
#define FOJ_STAGE246_PHASE_METER_H

/* Generated-only AArch64 evidence of four exclusive software-render steps.
 * Does not touch the gameplay state, output pixels or original PS3 assets. */
#include "isometric_demo.h"
#include <stdbool.h>
#include <stdint.h>

enum {
    FOJ_PHASE_METER_WINDOW = 32,
    FOJ_PHASE_METER_BITS = 16,
    FOJ_PHASE_METER_STEP = 4,
    FOJ_PHASE_METER_Y = 12,
    FOJ_PHASE_METER_TERRAIN_X = 948,
    FOJ_PHASE_METER_FORECAST_X = 1020,
    FOJ_PHASE_METER_MARKERS_X = 1092,
    FOJ_PHASE_METER_HUD_X = 1164,
    FOJ_PHASE_METER_STATUS_X = 1238
};

typedef struct {
    uint64_t terrain_total_ns;
    uint64_t forecast_total_ns;
    uint64_t marker_total_ns;
    uint64_t hud_total_ns;
    uint64_t whole_total_ns;
    uint16_t terrain_mean_us;
    uint16_t forecast_mean_us;
    uint16_t markers_mean_us;
    uint16_t hud_mean_us;
    uint32_t frame_count;
    uint32_t completed_windows;
    bool ready;
    bool failed;
    bool last_forecast_available;
} FojIsoPhaseMeter;

void foj_iso_phase_meter_init(FojIsoPhaseMeter *meter);
bool foj_iso_phase_meter_record(FojIsoPhaseMeter *meter,
                                const FojIsoPhaseReceipt *receipt);
bool foj_iso_phase_meter_draw(const FojIsoPhaseMeter *meter,
                              uint32_t *pixels, int width,
                              int height, int stride);
#endif
