#ifndef FOJ_STAGE248_BASE_PAIR_PROBE_H
#define FOJ_STAGE248_BASE_PAIR_PROBE_H
/* Generated-only CPU software-raster experiment; never touches PS3 data.
 * The large cache must live in static/heap memory, NOT the Switch stack. */
#include "isometric_demo.h"
#include <stdbool.h>
#include <stdint.h>
enum {
    FOJ_BASE_PAIR_WINDOW=32,
    FOJ_BASE_PAIR_BITS=16,
    FOJ_BASE_PAIR_STEP=4,
    FOJ_BASE_PAIR_CACHED_X=780,
    FOJ_BASE_PAIR_UNCACHED_X=852,
    FOJ_BASE_PAIR_STATUS_X=924,
    FOJ_BASE_PAIR_Y=12
};
typedef uint64_t (*FojBasePairClockNs)(void *);
typedef struct {
    FojIsoBaseCache base_cache;
    FojBattleThreatCache cached_threat;
    FojBattleThreatCache uncached_threat;
    FojBattle scene_key;
    uint64_t cached_sum_ns,uncached_sum_ns;
    uint32_t samples,total_pairs,completed_windows;
    uint16_t cached_mean_us,uncached_mean_us;
    bool key_valid,show_preview,ready,parity_ok,failed;
} FojBasePairProbe;

void foj_base_pair_init(FojBasePairProbe *probe);
/* Both variants render the identical full generated battle framebuffer into
 * private, distinct output buffers. Both threat caches are warmed equally,
 * and the base cache is warmed before paired measurement. AB/BA order changes
 * each pair. No display/GPU/present time, production cache, or gameplay input
 * is part of the timed section. Requires tightly packed buffers. */
bool foj_base_pair_step(FojBasePairProbe *probe,
                        const FojBattle *battle,bool show_preview,
                        uint32_t *cached_pixels,uint32_t *uncached_pixels,
                        int width,int height,int stride,
                        FojBasePairClockNs now_ns,void *ctx);
/* Two 16-bit average microsecond barcodes and 8x8 parity audit square.
 * Draw only after timing; never write into tested scratch buffers. */
bool foj_base_pair_draw(const FojBasePairProbe *probe,
                        uint32_t *pixels,int width,int height,int stride);
#endif
