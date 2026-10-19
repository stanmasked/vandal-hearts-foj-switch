#include "base_cache_stability_probe.h"
#include <limits.h>
#include <stddef.h>
#include <string.h>
#include "battle_scene_key.h"

void foj_base_stability_init(FojBaseStabilityProbe *p) {
    if (!p) return;
    foj_base_pair_init(&p->pair);
    p->cold_refill_us=p->warm_copy_us=0;
    p->cached_min_us=p->cached_max_us=0;
    p->uncached_min_us=p->uncached_max_us=0;
    p->worst_window_spread_us=0;
    p->observed_windows=p->scene_resets=0;
    p->cold_valid=p->ready=p->failed=false;
}
static bool fail(FojBaseStabilityProbe *p) {
    p->ready=false;
    p->failed=true;
    return false;
}
static bool valid_sample(uint64_t ns, uint16_t *us) {
    /* Avoid inventing a zero microsecond sample or silently clipping a
     * saturated 16-bit optical reading. */
    const uint64_t value=ns/UINT64_C(1000);
    if(value==0 || value>=UINT16_MAX) return false;
    *us=(uint16_t)value;
    return true;
}
bool foj_base_stability_step(FojBaseStabilityProbe *p,
                              const FojBattle *battle,bool show_preview,
                              uint32_t *cached_pixels,
                              uint32_t *uncached_pixels,
                              int width,int height,int stride,
                              FojBasePairClockNs clock_ns,void *ctx) {
    if(!p || !battle || !cached_pixels || !uncached_pixels ||
       cached_pixels==uncached_pixels || !clock_ns ||
       width<=0 || height<=0 || stride!=width ||
       width>FOJ_ISO_BASE_CACHE_WIDTH ||
       height>FOJ_ISO_BASE_CACHE_HEIGHT ||
       width>INT_MAX/height ||
       height>INT_MAX/(int)sizeof(uint32_t)/width ||
       p->failed) return false;
    const bool new_scene=!p->pair.key_valid ||
        p->pair.show_preview!=show_preview ||
        !foj_battle_scene_key_equal(&p->pair.scene_key,battle);
    if(new_scene) {
        /* Timed scope: one raw base-frame cold recompute followed by the
         * same exact-scene warm row-wise copy. No threat overlays here.
         * The Stage248 whole-battle AB/BA probe is independently reset
         * and warmed afterwards, entirely outside its paired clock. */
        p->cold_valid=false;
        p->ready=false;
        p->observed_windows=0;
        p->cached_min_us=p->cached_max_us=0;
        p->uncached_min_us=p->uncached_max_us=0;
        p->worst_window_spread_us=0;
        if(p->scene_resets==UINT32_MAX) return fail(p);
        ++p->scene_resets;
        foj_base_pair_init(&p->pair);
        FojDemo visual=battle->map;
        if(battle->enemy_hp==0) {
            visual.enemy_x=-1;
            visual.enemy_y=-1;
        }
        const uint64_t t0=clock_ns(ctx);
        const bool cold_hit=foj_iso_base_cache_draw(
            &p->pair.base_cache,&visual,cached_pixels,
            width,height,stride);
        const uint64_t t1=clock_ns(ctx);
        const bool warm_hit=foj_iso_base_cache_draw(
            &p->pair.base_cache,&visual,uncached_pixels,
            width,height,stride);
        const uint64_t t2=clock_ns(ctx);
        const size_t bytes=(size_t)width*(size_t)height*sizeof(uint32_t);
        if(cold_hit || !warm_hit || t1<=t0 || t2<=t1 ||
           memcmp(cached_pixels,uncached_pixels,bytes)!=0 ||
           !valid_sample(t1-t0,&p->cold_refill_us) ||
           !valid_sample(t2-t1,&p->warm_copy_us))
            return fail(p);
        p->cold_valid=true;
    }
    const uint32_t before=p->pair.completed_windows;
    if(!foj_base_pair_step(&p->pair,battle,show_preview,
        cached_pixels,uncached_pixels,width,height,stride,clock_ns,ctx))
        return fail(p);
    if(p->pair.completed_windows != before) {
        if(p->pair.completed_windows!=before+1 ||
           !p->pair.ready || !p->pair.parity_ok ||
           p->observed_windows==UINT32_MAX)
            return fail(p);
        const uint16_t a=p->pair.cached_mean_us;
        const uint16_t b=p->pair.uncached_mean_us;
        if(p->observed_windows==0) {
            p->cached_min_us=p->cached_max_us=a;
            p->uncached_min_us=p->uncached_max_us=b;
        } else {
            if(a<p->cached_min_us) p->cached_min_us=a;
            if(a>p->cached_max_us) p->cached_max_us=a;
            if(b<p->uncached_min_us) p->uncached_min_us=b;
            if(b>p->uncached_max_us) p->uncached_max_us=b;
        }
        ++p->observed_windows;
        const unsigned spread_a=p->cached_max_us-p->cached_min_us;
        const unsigned spread_b=p->uncached_max_us-p->uncached_min_us;
        p->worst_window_spread_us=(uint16_t)(spread_a>spread_b ?
                                               spread_a:spread_b);
        p->ready=p->cold_valid &&
            p->observed_windows>=FOJ_BASE_STABILITY_MIN_WINDOWS;
    }
    return true;
}
bool foj_base_stability_draw(const FojBaseStabilityProbe *p,
                              uint32_t *pixels,int width,int height,int stride) {
    if(!p || !pixels || width<FOJ_BASE_STABILITY_STATUS_X+8 ||
       height<FOJ_BASE_STABILITY_Y+8 || stride<width || stride<=0 ||
       height>INT_MAX/stride) return false;
    const uint32_t on[3]={
        UINT32_C(0xff3cd3aa), /* cold refill RGB=170,211,60 */
        UINT32_C(0xffd17caa), /* warm base copy RGB=170,124,209 */
        UINT32_C(0xff3a8cf5)  /* largest paired-window spread RGB=245,140,58 */
    };
    const uint16_t values[3]={
        p->cold_refill_us,p->warm_copy_us,p->worst_window_spread_us
    };
    const int x0[3]={
        FOJ_BASE_STABILITY_COLD_X,
        FOJ_BASE_STABILITY_WARM_X,
        FOJ_BASE_STABILITY_SPREAD_X
    };
    const uint32_t off=UINT32_C(0xff302530);
    const uint32_t pending=UINT32_C(0xffb28c51);
    const uint32_t ready_color=UINT32_C(0xff54e394);
    const uint32_t error=UINT32_C(0xff2929f4);
    for(int mode=0;mode<3;++mode) {
        for(int bit=0;bit<FOJ_BASE_STABILITY_BITS;++bit) {
            const int x=x0[mode]+bit*FOJ_BASE_STABILITY_STEP;
            const uint32_t color=p->failed || !p->ready ? pending :
                (values[mode] & (UINT16_C(1)<<bit)) ? on[mode]:off;
            for(int dy=0;dy<8;++dy)
                for(int dx=0;dx<3;++dx)
                    pixels[(FOJ_BASE_STABILITY_Y+dy)*stride+x+dx]=color;
        }
    }
    const uint32_t status=p->failed ? error :
                          p->ready ? ready_color : pending;
    for(int dy=0;dy<8;++dy)
        for(int dx=0;dx<8;++dx)
            pixels[(FOJ_BASE_STABILITY_Y+dy)*stride+
                FOJ_BASE_STABILITY_STATUS_X+dx]=status;
    return true;
}
