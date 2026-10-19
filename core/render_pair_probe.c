#include "render_pair_probe.h"
#include <limits.h>
#include <stddef.h>
#include <string.h>

void foj_render_pair_init(FojRenderPairProbe *meter) {
    if (!meter) return;
    memset(meter, 0, sizeof(*meter));
    foj_battle_threat_cache_init(&meter->cache);
    meter->parity_ok = true;
}

static bool same_key(const FojRenderPairProbe *meter,
                     const FojBattle *battle, bool show) {
    if (!meter->state_valid || show != meter->show_threat_preview)
        return false;
    FojBattle normalized = *battle;
    normalized.map.cursor_x = 0;
    normalized.map.cursor_y = 0;
    return memcmp(&normalized, &meter->key, sizeof(normalized)) == 0;
}

static bool render_timed(FojRenderPairProbe *meter,
                         const FojBattle *battle, bool show,
                         uint32_t *pixels, int width, int height, int stride,
                         bool use_cache, FojRenderPairClockNs clock_ns,
                         void *clock_context, uint64_t *elapsed) {
    const uint64_t start = clock_ns(clock_context);
    foj_iso_render_battle_cached_options(battle,pixels,width,height,stride,show,
                                        use_cache ? &meter->cache : NULL);
    const uint64_t finish = clock_ns(clock_context);
    if (finish <= start) return false;
    *elapsed = finish - start;
    return true;
}

bool foj_render_pair_step(FojRenderPairProbe *meter,
                          const FojBattle *battle, bool show_preview,
                          uint32_t *cached_pixels, uint32_t *uncached_pixels,
                          int width, int height, int stride,
                          FojRenderPairClockNs clock_ns, void *context) {
    if (!meter || !battle || !cached_pixels || !uncached_pixels ||
        cached_pixels == uncached_pixels || !clock_ns || width<=0 ||
        height<=0 || stride!=width || width>INT_MAX/height ||
        height>INT_MAX/(int)sizeof(uint32_t)/width ||
        meter->failed) return false;

    if (!same_key(meter,battle,show_preview)) {
        foj_render_pair_init(meter);
        meter->key = *battle;
        meter->key.map.cursor_x = meter->key.map.cursor_y = 0;
        meter->state_valid = true;
        meter->show_threat_preview = show_preview;
    }
    /* Warm the private cache outside the timed interval if applicable.
     * The production render cache is a completely separate object. */
    if (show_preview && battle->outcome==FOJ_BATTLE_ONGOING &&
        battle->map.selected && !battle->moved_this_turn) {
        FojBattleThreatPreview warm;
        if (!foj_battle_preview_movement_threat_cached(
                &meter->cache,battle,&warm)) {
            meter->failed=true;meter->parity_ok=false;meter->ready=false;
            return false;
        }
    }

    uint64_t cached_ns=0,uncached_ns=0;
    bool ok;
    if ((meter->total_pairs & 1u)==0u) {
        ok=render_timed(meter,battle,show_preview,cached_pixels,
                        width,height,stride,true,clock_ns,context,&cached_ns) &&
           render_timed(meter,battle,show_preview,uncached_pixels,
                        width,height,stride,false,clock_ns,context,&uncached_ns);
    } else {
        ok=render_timed(meter,battle,show_preview,uncached_pixels,
                        width,height,stride,false,clock_ns,context,&uncached_ns) &&
           render_timed(meter,battle,show_preview,cached_pixels,
                        width,height,stride,true,clock_ns,context,&cached_ns);
    }
    const size_t bytes=(size_t)width*(size_t)height*sizeof(uint32_t);
    if (!ok || memcmp(cached_pixels,uncached_pixels,bytes)!=0 ||
        UINT64_MAX-meter->cached_sum_ns<cached_ns ||
        UINT64_MAX-meter->uncached_sum_ns<uncached_ns ||
        meter->total_pairs==UINT32_MAX) {
        meter->failed=true;meter->parity_ok=false;meter->ready=false;
        return false;
    }
    meter->cached_sum_ns+=cached_ns;
    meter->uncached_sum_ns+=uncached_ns;
    ++meter->samples;
    ++meter->total_pairs;
    if (meter->samples==FOJ_RENDER_PAIR_WINDOW) {
        const uint64_t denominator=FOJ_RENDER_PAIR_WINDOW*UINT64_C(1000);
        const uint64_t cached_us=meter->cached_sum_ns/denominator;
        const uint64_t uncached_us=meter->uncached_sum_ns/denominator;
        if (!cached_us || !uncached_us ||
            cached_us>=FOJ_RENDER_PAIR_MAX_US ||
            uncached_us>=FOJ_RENDER_PAIR_MAX_US) {
            meter->failed=true;meter->ready=false;return false;
        }
        meter->cached_mean_us=(uint32_t)cached_us;
        meter->uncached_mean_us=(uint32_t)uncached_us;
        ++meter->completed_windows;
        meter->samples=0;
        meter->cached_sum_ns=meter->uncached_sum_ns=0;
        meter->ready=true;
    }
    return true;
}

bool foj_render_pair_draw(const FojRenderPairProbe *meter,
                          uint32_t *pixels, int width, int height, int stride) {
    if (!meter || !pixels || width<FOJ_RENDER_PAIR_STATUS_X+8 ||
        height<FOJ_RENDER_PAIR_Y+8 || stride<width || stride<=0 ||
        height>INT_MAX/stride) return false;
    const uint32_t pending=UINT32_C(0xffb8863f);
    const uint32_t off=UINT32_C(0xff302530);
    const uint32_t cached_on=UINT32_C(0xfff1d43e);
    const uint32_t uncached_on=UINT32_C(0xff2d81ec);
    const uint32_t status=meter->failed ? UINT32_C(0xff2222ff) :
        meter->ready && meter->parity_ok ? UINT32_C(0xff68e85b) : pending;
    for(unsigned bit=0;bit<FOJ_RENDER_PAIR_BITS;++bit) {
        for(unsigned mode=0;mode<2;++mode) {
            const int x=(mode ? FOJ_RENDER_PAIR_UNCACHED_X :
                                FOJ_RENDER_PAIR_CACHED_X)+
                        (int)bit*FOJ_RENDER_PAIR_BAR_STEP;
            const uint32_t value=mode ? meter->uncached_mean_us :
                                        meter->cached_mean_us;
            const uint32_t color=!meter->ready || meter->failed ? pending :
                (value & (UINT32_C(1)<<bit)) ?
                    (mode ? uncached_on : cached_on) : off;
            for(int y=0;y<8;++y)
                for(int dx=0;dx<3;++dx)
                    pixels[(FOJ_RENDER_PAIR_Y+y)*stride+x+dx]=color;
        }
    }
    for(int y=0;y<8;++y)
        for(int x=0;x<8;++x)
            pixels[(FOJ_RENDER_PAIR_Y+y)*stride+FOJ_RENDER_PAIR_STATUS_X+x]=status;
    return true;
}
