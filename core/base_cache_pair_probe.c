/* Stage248: controlled in-process scene-exact base-raster A/B.
 * This is a CPU raster benchmark in a synthetic battle, not Switch FPS. */
#include "base_cache_pair_probe.h"
#include <limits.h>
#include <stddef.h>
#include <string.h>
#include "battle_scene_key.h"

void foj_base_pair_init(FojBasePairProbe *probe) {
    if (!probe) return;
    foj_iso_base_cache_init(&probe->base_cache);
    foj_battle_threat_cache_init(&probe->cached_threat);
    foj_battle_threat_cache_init(&probe->uncached_threat);
    probe->cached_sum_ns=probe->uncached_sum_ns=0;
    probe->samples=probe->total_pairs=probe->completed_windows=0;
    probe->cached_mean_us=probe->uncached_mean_us=0;
    probe->key_valid=probe->show_preview=probe->ready=probe->failed=false;
    probe->parity_ok=true;
}
static bool render_once(FojBasePairProbe *probe,const FojBattle *battle,
                        bool show,uint32_t *output,int width,int height,
                        int stride,bool use_base,FojBasePairClockNs now,
                        void *ctx,uint64_t *elapsed_ns) {
    bool hit=false;
    const uint64_t before=now(ctx);
    foj_iso_render_battle_profiled_base_cached(
        battle,output,width,height,stride,show,
        use_base ? &probe->cached_threat : &probe->uncached_threat,
        use_base ? &probe->base_cache : NULL,&hit,NULL,NULL,NULL);
    const uint64_t after=now(ctx);
    if(after<=before || (use_base && !hit)) return false;
    *elapsed_ns=after-before;
    return true;
}
static void warm(FojBasePairProbe *probe,const FojBattle *battle,bool show,
                 uint32_t *cached_pixels,uint32_t *uncached_pixels,
                 int width,int height,int stride) {
    bool hit=false;
    /* Same full renderer on both paths. Uncached baseline uses no base
     * storage; each arm has a separate, equally warmed threat matrix. */
    foj_iso_render_battle_profiled_base_cached(
        battle,cached_pixels,width,height,stride,show,
        &probe->cached_threat,&probe->base_cache,&hit,NULL,NULL,NULL);
    foj_iso_render_battle_profiled_base_cached(
        battle,uncached_pixels,width,height,stride,show,
        &probe->uncached_threat,NULL,NULL,NULL,NULL,NULL);
}
static bool fail(FojBasePairProbe *probe) {
    probe->failed=true;
    probe->parity_ok=false;
    probe->ready=false;
    return false;
}
bool foj_base_pair_step(FojBasePairProbe *probe,
                        const FojBattle *battle,bool show_preview,
                        uint32_t *cached_pixels,uint32_t *uncached_pixels,
                        int width,int height,int stride,
                        FojBasePairClockNs now_ns,void *ctx) {
    if(!probe || !battle || !cached_pixels || !uncached_pixels ||
       cached_pixels==uncached_pixels || !now_ns ||
       width<=0 || height<=0 || stride!=width ||
       width>FOJ_ISO_BASE_CACHE_WIDTH ||
       height>FOJ_ISO_BASE_CACHE_HEIGHT ||
       width>INT_MAX/height ||
       height>INT_MAX/(int)sizeof(uint32_t)/width ||
       probe->failed) return false;
    if(!probe->key_valid || probe->show_preview!=show_preview ||
       !foj_battle_scene_key_equal(&probe->scene_key,battle)) {
        foj_base_pair_init(probe);
        probe->scene_key=*battle;
        probe->show_preview=show_preview;
        probe->key_valid=true;
        warm(probe,battle,show_preview,cached_pixels,uncached_pixels,
             width,height,stride);
    }
    uint64_t a=0,b=0;
    bool ok;
    /* True AB/BA order, within the SAME emulator process and scene. */
    if((probe->total_pairs & 1u)==0u) {
        ok=render_once(probe,battle,show_preview,cached_pixels,
                       width,height,stride,true,now_ns,ctx,&a) &&
           render_once(probe,battle,show_preview,uncached_pixels,
                       width,height,stride,false,now_ns,ctx,&b);
    } else {
        ok=render_once(probe,battle,show_preview,uncached_pixels,
                       width,height,stride,false,now_ns,ctx,&b) &&
           render_once(probe,battle,show_preview,cached_pixels,
                       width,height,stride,true,now_ns,ctx,&a);
    }
    const size_t byte_count=(size_t)width*(size_t)height*sizeof(uint32_t);
    if(!ok || memcmp(cached_pixels,uncached_pixels,byte_count)!=0 ||
       UINT64_MAX-probe->cached_sum_ns<a ||
       UINT64_MAX-probe->uncached_sum_ns<b ||
       probe->total_pairs==UINT32_MAX) return fail(probe);
    probe->cached_sum_ns+=a;
    probe->uncached_sum_ns+=b;
    ++probe->samples;
    ++probe->total_pairs;
    if(probe->samples==FOJ_BASE_PAIR_WINDOW) {
        const uint64_t div=FOJ_BASE_PAIR_WINDOW*UINT64_C(1000);
        const uint64_t a_us=probe->cached_sum_ns/div;
        const uint64_t b_us=probe->uncached_sum_ns/div;
        if(a_us==0 || b_us==0 || a_us>=UINT16_MAX ||
           b_us>=UINT16_MAX || probe->completed_windows==UINT32_MAX)
            return fail(probe);
        probe->cached_mean_us=(uint16_t)a_us;
        probe->uncached_mean_us=(uint16_t)b_us;
        probe->cached_sum_ns=probe->uncached_sum_ns=0;
        probe->samples=0;
        ++probe->completed_windows;
        probe->ready=true;
    }
    return true;
}
bool foj_base_pair_draw(const FojBasePairProbe *probe,
                        uint32_t *pixels,int width,int height,int stride) {
    if(!probe || !pixels || width<FOJ_BASE_PAIR_STATUS_X+8 ||
       height<FOJ_BASE_PAIR_Y+8 || stride<width ||
       stride<=0 || height>INT_MAX/stride) return false;
    const uint32_t pending=UINT32_C(0xffad8245);
    const uint32_t off=UINT32_C(0xff302530);
    const uint32_t cached=UINT32_C(0xff41bcf3);
    const uint32_t uncached=UINT32_C(0xffea8557);
    const uint32_t ready=UINT32_C(0xff4be87d);
    const uint32_t failed=UINT32_C(0xff3030ff);
    for(int bit=0;bit<FOJ_BASE_PAIR_BITS;++bit) {
        for(int mode=0;mode<2;++mode) {
            const int x=(mode ? FOJ_BASE_PAIR_UNCACHED_X :
                                    FOJ_BASE_PAIR_CACHED_X)+bit*FOJ_BASE_PAIR_STEP;
            const uint32_t value=mode ? probe->uncached_mean_us :
                                        probe->cached_mean_us;
            const uint32_t color=!probe->ready || probe->failed ? pending :
                (value & (UINT32_C(1)<<bit)) ?
                (mode ? uncached:cached) : off;
            for(int dy=0;dy<8;++dy)
                for(int dx=0;dx<3;++dx)
                    pixels[(FOJ_BASE_PAIR_Y+dy)*stride+x+dx]=color;
        }
    }
    const uint32_t status=probe->failed ? failed :
        (probe->ready && probe->parity_ok ? ready:pending);
    for(int dy=0;dy<8;++dy)
        for(int dx=0;dx<8;++dx)
            pixels[(FOJ_BASE_PAIR_Y+dy)*stride+FOJ_BASE_PAIR_STATUS_X+dx]=status;
    return true;
}
