#ifndef FOJ_COMPACT_STRESS_PROBE_H
#define FOJ_COMPACT_STRESS_PROBE_H
/* Stage252 research-only stress. No original PS3 content or FPS claims. */
#include "base_cache_compact.h"
#include <stdbool.h>
#include <stdint.h>
enum {
    FOJ_COMPACT_STRESS_ITERATIONS=96,
    FOJ_COMPACT_STRESS_FAULT_DIVISOR=13,
    FOJ_COMPACT_STRESS_Y=60,
    FOJ_COMPACT_STRESS_FIRST_X=536,
    FOJ_COMPACT_STRESS_STATUS_X=824
};
typedef struct {
    uint16_t cycles;
    uint16_t injected_failures;
    uint16_t allocations;
    uint16_t releases;
    uint16_t peak_kib;
    bool passed;
} FojCompactStressReceipt;

/* Caller owns two >=1280x720-pixel scratch buffers. Unlike Stage251,
 * this test alters dimensions and the generated battle state 96 times. */
bool foj_compact_stress_run(FojCompactStressReceipt *out,
                            uint32_t *cached,uint32_t *reference);
bool foj_compact_stress_draw(const FojCompactStressReceipt *out,
                             uint32_t *pixels,int width,int height,int stride);
#endif
