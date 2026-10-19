#include "threat_pair_probe.h"

#include <limits.h>
#include <stddef.h>
#include <string.h>

void foj_threat_pair_probe_init(FojThreatPairProbe *probe) {
    if (!probe) return;
    memset(probe, 0, sizeof(*probe));
    foj_battle_threat_cache_init(&probe->experimental_cache);
    probe->parity_ok = true;
}

static bool eligible(const FojBattle *battle) {
    return battle && battle->outcome == FOJ_BATTLE_ONGOING &&
        battle->map.selected && !battle->moved_this_turn &&
        foj_in_bounds(battle->map.hero_x,battle->map.hero_y) &&
        foj_in_bounds(battle->map.enemy_x,battle->map.enemy_y);
}

static bool measure_mode(FojThreatPairProbe *probe, const FojBattle *battle,
                         bool cached, FojPairNowNs now_ns, void *clock_context,
                         FojBattleThreatPreview *result,
                         uint64_t *elapsed_ns) {
    FojBattleThreatPreview comparison;
    uint64_t start = now_ns(clock_context);
    for (unsigned i = 0; i < FOJ_PAIR_PROBE_REPEATS; ++i) {
        FojBattleThreatPreview current;
        if (!foj_battle_preview_movement_threat_cached(
                cached ? &probe->experimental_cache : NULL,
                battle, &current))
            return false;
        if (i == 0) comparison = current;
        else if (memcmp(&comparison, &current, sizeof(current)) != 0)
            return false;
    }
    uint64_t end = now_ns(clock_context);
    if (end <= start) return false;
    *result = comparison;
    *elapsed_ns = end - start;
    return true;
}

bool foj_threat_pair_probe_step(FojThreatPairProbe *probe,
                               const FojBattle *battle,
                               FojPairNowNs now_ns, void *clock_context) {
    if (!probe || !now_ns) return false;
    if (!eligible(battle)) {
        /* No forecast should be timed in disabled/invalid game states. */
        foj_threat_pair_probe_init(probe);
        return false;
    }
    FojBattle key = *battle;
    key.map.cursor_x = 0;
    key.map.cursor_y = 0;
    if (!probe->key_valid || memcmp(&probe->key, &key, sizeof(key))) {
        foj_threat_pair_probe_init(probe);
        probe->key = key;
        probe->key_valid = true;
    }
    if (probe->failed) return false;

    FojBattleThreatPreview warm;
    if (!foj_battle_preview_movement_threat_cached(
            &probe->experimental_cache, battle, &warm)) {
        probe->failed = true;
        probe->ready = false;
        return false;
    }

    FojBattleThreatPreview cached, uncached;
    uint64_t a = 0, b = 0;
    bool ok;
    if ((probe->total_pairs & 1u) == 0u) {
        ok = measure_mode(probe,battle,true,now_ns,clock_context,&cached,&a) &&
             measure_mode(probe,battle,false,now_ns,clock_context,&uncached,&b);
    } else {
        ok = measure_mode(probe,battle,false,now_ns,clock_context,&uncached,&b) &&
             measure_mode(probe,battle,true,now_ns,clock_context,&cached,&a);
    }
    if (!ok || memcmp(&cached,&uncached,sizeof(cached)) != 0 ||
        memcmp(&cached,&warm,sizeof(cached)) != 0 ||
        UINT64_MAX - probe->cached_total_ns < a ||
        UINT64_MAX - probe->uncached_total_ns < b ||
        probe->total_pairs == UINT32_MAX) {
        probe->parity_ok = false;
        probe->failed = true;
        probe->ready = false;
        return false;
    }
    probe->cached_total_ns += a;
    probe->uncached_total_ns += b;
    ++probe->total_pairs;
    ++probe->pair_count;
    if (probe->pair_count == FOJ_PAIR_PROBE_WINDOW) {
        const uint64_t divisor = FOJ_PAIR_PROBE_WINDOW *
                                 (uint64_t)FOJ_PAIR_PROBE_REPEATS;
        const uint64_t cached_mean = probe->cached_total_ns / divisor;
        const uint64_t uncached_mean = probe->uncached_total_ns / divisor;
        if (!cached_mean || !uncached_mean ||
            cached_mean >= FOJ_PAIR_PROBE_MAX_NS ||
            uncached_mean >= FOJ_PAIR_PROBE_MAX_NS) {
            probe->failed = true;
            probe->ready = false;
            return false;
        }
        probe->cached_mean_ns = (uint32_t)cached_mean;
        probe->uncached_mean_ns = (uint32_t)uncached_mean;
        probe->ready = true;
        ++probe->completed_windows;
        probe->pair_count = 0;
        probe->cached_total_ns = 0;
        probe->uncached_total_ns = 0;
    }
    return true;
}

bool foj_threat_pair_probe_draw(const FojThreatPairProbe *probe,
                               uint32_t *pixels, int width, int height,
                               int stride) {
    if (!probe || !pixels || width < FOJ_PAIR_PROBE_STATUS_X+8 ||
        height < FOJ_PAIR_PROBE_Y+8 || stride < width || stride <= 0 ||
        height > INT_MAX / stride) return false;
    const uint32_t pending = UINT32_C(0xffb8863f);
    const uint32_t off = UINT32_C(0xff302530);
    const uint32_t on_cached = UINT32_C(0xff33aa6f);
    const uint32_t on_uncached = UINT32_C(0xffa36fe5);
    const uint32_t status = probe->failed ? UINT32_C(0xff2222ff) :
        probe->ready && probe->parity_ok ? UINT32_C(0xff33c956) : pending;
    for (unsigned bit=0; bit<FOJ_PAIR_PROBE_BITS; ++bit) {
        for (unsigned mode=0; mode<2; ++mode) {
            const int xx = (mode ? FOJ_PAIR_PROBE_UNCACHED_X :
                                  FOJ_PAIR_PROBE_CACHED_X) +
                           (int)bit*FOJ_PAIR_PROBE_STEP;
            uint32_t value = mode ? probe->uncached_mean_ns :
                                    probe->cached_mean_ns;
            uint32_t color = !probe->ready || probe->failed ? pending :
                (value & (UINT32_C(1)<<bit)) ?
                    (mode ? on_uncached : on_cached) : off;
            for (int dy=0; dy<8; ++dy)
                for (int dx=0; dx<3; ++dx)
                    pixels[(FOJ_PAIR_PROBE_Y+dy)*stride+xx+dx] = color;
        }
    }
    for (int dy=0; dy<8; ++dy)
        for (int dx=0; dx<8; ++dx)
            pixels[(FOJ_PAIR_PROBE_Y+dy)*stride+
                   FOJ_PAIR_PROBE_STATUS_X+dx] = status;
    return true;
}
