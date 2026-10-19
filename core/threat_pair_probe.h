#ifndef FOJ_STAGE244_THREAT_PAIR_PROBE_H
#define FOJ_STAGE244_THREAT_PAIR_PROBE_H

/* Generated-only, caller-owned forecast microbenchmark. A cache hit and
 * a real uncached recomputation are evaluated on identical immutable battle
 * input inside a SINGLE Switch guest process. Never touches gameplay state,
 * GPU timing, frame presentation or original PS3 resources. */
#include <stdbool.h>
#include <stdint.h>
#include "tactical_battle.h"

enum {
    FOJ_PAIR_PROBE_REPEATS = 16,
    FOJ_PAIR_PROBE_WINDOW = 32,
    FOJ_PAIR_PROBE_BITS = 24,
    FOJ_PAIR_PROBE_STEP = 4,
    FOJ_PAIR_PROBE_CACHED_X = 528,
    FOJ_PAIR_PROBE_UNCACHED_X = 644,
    FOJ_PAIR_PROBE_Y = 12,
    FOJ_PAIR_PROBE_STATUS_X = 752,
    FOJ_PAIR_PROBE_MAX_NS = 16777215
};

typedef uint64_t (*FojPairNowNs)(void *);

typedef struct {
    FojBattleThreatCache experimental_cache;
    FojBattle key;
    uint64_t cached_total_ns;
    uint64_t uncached_total_ns;
    uint32_t cached_mean_ns;
    uint32_t uncached_mean_ns;
    uint32_t pair_count;
    uint32_t total_pairs;
    uint32_t completed_windows;
    bool key_valid;
    bool ready;
    bool parity_ok;
    bool failed;
} FojThreatPairProbe;

void foj_threat_pair_probe_init(FojThreatPairProbe *probe);
/* Returns true only when an actual valid pair was sampled.
 * Alternate cached-first / uncached-first order on consecutive pairs.
 * Each 32-pair window reports nanoseconds per forecast CALL (16 repeats
 * per mode per pair). Cached path is WARM before the timed region. */
bool foj_threat_pair_probe_step(FojThreatPairProbe *probe,
                                 const FojBattle *battle,
                                 FojPairNowNs now_ns, void *clock_context);
/* Emits 24 low-bit-first nanosecond bars and an 8x8 audit tile. Fail closed
 * on incomplete window, invalid timings, parity or undersized framebuffer. */
bool foj_threat_pair_probe_draw(const FojThreatPairProbe *probe,
                                 uint32_t *pixels, int width,
                                 int height, int stride);
#endif
