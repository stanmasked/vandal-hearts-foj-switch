#ifndef FOJ_COMPACT_BUDGET_PROBE_H
#define FOJ_COMPACT_BUDGET_PROBE_H
/* Stage255 generated-only tight-budget cache parity, no real PS3 content. */
#include "compact_churn_probe.h"
#include <stdbool.h>
#include <stdint.h>
enum {
    FOJ_BUDGET_FRAMES=384,
    FOJ_BUDGET_Y=108,
    FOJ_BUDGET_X=536,
    FOJ_BUDGET_STATUS_X=968
};
typedef struct {
    uint16_t frames, allocations, releases, hits, misses, fallback_blocks;
    bool passed;
} FojBudgetReceipt;
/* Two caller-owned buffers each hold at least 1280x720 RGBA pixels.
 * Every frame uses an exact-payload budget; fallback is required in all
 * 16 of the 320x180 blocks and output must match uncached pixels. */
bool foj_budget_probe_run(FojBudgetReceipt *out,
                          uint32_t *cached,uint32_t *reference);
bool foj_budget_probe_draw(const FojBudgetReceipt *out,
                           uint32_t *pixels,int width,int height,int stride);
#endif
