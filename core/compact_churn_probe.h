#ifndef FOJ_COMPACT_CHURN_PROBE_H
#define FOJ_COMPACT_CHURN_PROBE_H
/* Stage253: synthetic CPU cache allocation churn; no GPU, PS3 or RSS. */
#include "base_cache_compact.h"
#include <stdbool.h>
#include <stdint.h>
enum {
    FOJ_CHURN_STEPS=384, FOJ_CHURN_BLOCK=8,
    FOJ_CHURN_Y=76, FOJ_CHURN_X=536, FOJ_CHURN_STATUS_X=968
};
typedef struct {
    uint16_t steps, allocations, releases, hits, misses, peak_kib;
    bool passed;
} FojCompactChurnReceipt;

/* Each scratch buffer must hold at least 1280*720 RGBA pixels.
 * 48 blocks alternate three resolutions, four scene keys/block,
 * with immediate repetitions of each key. */
bool foj_compact_churn_run(FojCompactChurnReceipt *out,
                           uint32_t *cached,uint32_t *reference);
bool foj_compact_churn_draw(const FojCompactChurnReceipt *out,
                            uint32_t *pixels,int width,int height,int stride);
#endif
