#ifndef FOJ_STAGE249_BASE_STABILITY_PROBE_H
#define FOJ_STAGE249_BASE_STABILITY_PROBE_H
/* Stage249: repeated in-process AB/BA windows plus cold/refill cost.
 * Generated-only CPU raster research, never original FoJ PS3 data. */
#include "base_cache_pair_probe.h"
#include <stdbool.h>
#include <stdint.h>
enum {
    FOJ_BASE_STABILITY_MIN_WINDOWS=3,
    FOJ_BASE_STABILITY_BITS=16,
    FOJ_BASE_STABILITY_STEP=4,
    FOJ_BASE_STABILITY_COLD_X=536,
    FOJ_BASE_STABILITY_WARM_X=608,
    FOJ_BASE_STABILITY_SPREAD_X=680,
    FOJ_BASE_STABILITY_STATUS_X=752,
    FOJ_BASE_STABILITY_Y=12
};
typedef struct {
    FojBasePairProbe pair;
    uint16_t cold_refill_us, warm_copy_us;
    uint16_t cached_min_us,cached_max_us;
    uint16_t uncached_min_us,uncached_max_us;
    uint16_t worst_window_spread_us;
    uint32_t observed_windows, scene_resets;
    bool cold_valid,ready,failed;
} FojBaseStabilityProbe;

/* Caller must allocate the probe and both full-raster scratch buffers in
 * static storage/heap, never on a Switch thread's stack. */
void foj_base_stability_init(FojBaseStabilityProbe *probe);
bool foj_base_stability_step(FojBaseStabilityProbe *probe,
                              const FojBattle *battle,bool show_preview,
                              uint32_t *cached_pixels,
                              uint32_t *uncached_pixels,
                              int width,int height,int stride,
                              FojBasePairClockNs clock_ns,void *ctx);
bool foj_base_stability_draw(const FojBaseStabilityProbe *probe,
                              uint32_t *pixels,int width,int height,int stride);
#endif
