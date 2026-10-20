#ifndef FOJ_STAGE250_BASE_CACHE_SCALE_PROBE_H
#define FOJ_STAGE250_BASE_CACHE_SCALE_PROBE_H
/* Opt-in research: three resolutions, true cold refill and warm base copy.
 * Only generated FoJ terrain; neither GPU timing nor real PS3 resources. */
#include "base_cache_pair_probe.h"
#ifndef FOJ_STAGE251_COMPACT
#define FOJ_STAGE251_COMPACT 0
#endif
#if FOJ_STAGE251_COMPACT != 0 && FOJ_STAGE251_COMPACT != 1
#error "Stage251 compact experiment requires flag 0 or 1"
#endif
#if FOJ_STAGE251_COMPACT
#include "base_cache_compact.h"
#endif
#include <stdbool.h>
#include <stdint.h>
enum {
    FOJ_BASE_SCALE_MODES=3,
    FOJ_BASE_SCALE_BITS=16,
    FOJ_BASE_SCALE_STEP=4,
    FOJ_BASE_SCALE_Y=28,
    FOJ_BASE_SCALE_FIRST_X=536,
    FOJ_BASE_SCALE_STATUS_X=968
};
typedef struct {
#if FOJ_STAGE251_COMPACT
    FojCompactBaseCache cache;
    uint16_t requested_kib[FOJ_BASE_SCALE_MODES];
#else
    FojIsoBaseCache cache;
#endif
    FojBattle scene_key;
    uint16_t cold_us[FOJ_BASE_SCALE_MODES];
    uint16_t warm_us[FOJ_BASE_SCALE_MODES];
    uint32_t scene_resets;
    uint32_t active_bytes[FOJ_BASE_SCALE_MODES];
    bool key_valid, preview, ready, failed;
} FojBaseScaleProbe;
void foj_base_scale_init(FojBaseScaleProbe *probe);
#if FOJ_STAGE251_COMPACT
/* Must release after the last sample, including any host-only test. */
void foj_base_scale_release(FojBaseScaleProbe *probe);
bool foj_base_scale_draw_memory(const FojBaseScaleProbe *probe,
                                uint32_t *pixels,int width,int height,int stride);
enum { FOJ_BASE_COMPACT_Y=44, FOJ_BASE_COMPACT_X=536,
       FOJ_BASE_COMPACT_STATUS_X=752 };
#endif
/* Distinct private scratch buffers have full 1280x720 capacity. For each
 * size, require a miss then an exact hit, verify byte parity and independent
 * foj_iso_render reference. Timings include only base operations. A changed
 * scene or forecast visibility triggers all sizes again, never cherry-picks. */
bool foj_base_scale_step(FojBaseScaleProbe *probe,const FojBattle *battle,
                         bool preview,uint32_t *scratch_a,
                         uint32_t *scratch_b,
                         FojBasePairClockNs clock_ns,void *ctx);
bool foj_base_scale_draw(const FojBaseScaleProbe *probe,
                         uint32_t *pixels,int width,int height,int stride);
#endif
