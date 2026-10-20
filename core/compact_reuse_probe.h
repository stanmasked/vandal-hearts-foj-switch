#ifndef FOJ_COMPACT_REUSE_PROBE_H
#define FOJ_COMPACT_REUSE_PROBE_H
/* Stage254: controlled 384-frame allocation/capacity tradeoff. No PS3 assets. */
#include "compact_churn_probe.h"
#include <stdbool.h>
#include <stdint.h>
enum {
    FOJ_REUSE_FRAMES=384,
    FOJ_REUSE_FLOOR_KIB=900,
    FOJ_REUSE_Y=92,
    FOJ_REUSE_X=536,
    FOJ_REUSE_STATUS_X=968
};
typedef struct {
    uint16_t frames, exact_allocations, reuse_allocations;
    uint16_t reuse_releases, allocations_saved, extra_small_kib;
    bool passed;
} FojReuseReceipt;
/* Uses Stage253 receipt as independent exact-size baseline.
 * One extra 384-frame run with 900-KiB floor; 1280x720 must remain exact. */
bool foj_reuse_probe_run(FojReuseReceipt *out,
                         const FojCompactChurnReceipt *baseline,
                         uint32_t *cached,uint32_t *reference);
bool foj_reuse_probe_draw(const FojReuseReceipt *out,
                          uint32_t *pixels,int width,int height,int stride);
#endif
