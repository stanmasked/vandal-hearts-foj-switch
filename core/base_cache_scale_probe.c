/* Stage250: controlled cross-resolution cold/warm CPU raster measurements. */
#include "base_cache_scale_probe.h"
#include <limits.h>
#include <stddef.h>
#include <string.h>
#include "battle_scene_key.h"

static const int modes[FOJ_BASE_SCALE_MODES][2]={
    {320,180},{640,360},{1280,720}
};
static const uint32_t bytes[FOJ_BASE_SCALE_MODES]={
    UINT32_C(230400),UINT32_C(921600),UINT32_C(3686400)
};
void foj_base_scale_init(FojBaseScaleProbe *p) {
    if(!p)return;
#if FOJ_STAGE251_COMPACT
    foj_compact_base_init(&p->cache);
#else
    foj_iso_base_cache_init(&p->cache);
#endif
    for(int i=0;i<FOJ_BASE_SCALE_MODES;++i) {
        p->cold_us[i]=p->warm_us[i]=0;
        p->active_bytes[i]=bytes[i];
#if FOJ_STAGE251_COMPACT
        p->requested_kib[i]=0;
#endif
    }
    p->scene_resets=0;
    p->key_valid=p->preview=p->ready=p->failed=false;
}
static bool fail(FojBaseScaleProbe *p) {
#if FOJ_STAGE251_COMPACT
    foj_compact_base_release(&p->cache);
#endif
    p->failed=true;
    p->ready=false;
    return false;
}
static bool sample(uint64_t start,uint64_t end,uint16_t *microseconds) {
    if(end<=start)return false;
    uint64_t us=(end-start)/UINT64_C(1000);
    if(us==0 || us>=UINT16_MAX)return false;
    *microseconds=(uint16_t)us;
    return true;
}
bool foj_base_scale_step(FojBaseScaleProbe *p,const FojBattle *battle,
                         bool preview,uint32_t *a,uint32_t *b,
                         FojBasePairClockNs clock_ns,void *ctx) {
    if(!p || !battle || !a || !b || a==b || !clock_ns || p->failed)
        return false;
    const bool changed=!p->key_valid || p->preview!=preview ||
                       !foj_battle_scene_key_equal(&p->scene_key,battle);
    if(!changed) return p->ready;
    if(p->scene_resets==UINT32_MAX)return fail(p);
    ++p->scene_resets;
    p->ready=false;
    p->key_valid=false;
#if FOJ_STAGE251_COMPACT
    foj_compact_base_reset(&p->cache);
#else
    foj_iso_base_cache_init(&p->cache);
#endif
    FojDemo visual=battle->map;
    if(battle->enemy_hp==0) {
        visual.enemy_x=-1;
        visual.enemy_y=-1;
    }
    for(int i=0;i<FOJ_BASE_SCALE_MODES;++i) {
        const int width=modes[i][0],height=modes[i][1];
        const size_t used=(size_t)width*(size_t)height*sizeof(uint32_t);
        const uint64_t before=clock_ns(ctx);
#if FOJ_STAGE251_COMPACT
        const int cold_hit=foj_compact_base_draw(
            &p->cache,&visual,a,width,height,width);
#else
        const bool cold_hit=foj_iso_base_cache_draw(
            &p->cache,&visual,a,width,height,width);
#endif
        const uint64_t mid=clock_ns(ctx);
#if FOJ_STAGE251_COMPACT
        const int warm_hit=foj_compact_base_draw(
            &p->cache,&visual,b,width,height,width);
#else
        const bool warm_hit=foj_iso_base_cache_draw(
            &p->cache,&visual,b,width,height,width);
#endif
        const uint64_t after=clock_ns(ctx);
#if FOJ_STAGE251_COMPACT
        if(cold_hit!=0 || warm_hit!=1 ||
           p->cache.allocated_bytes!=used ||
           used%1024u!=0 || used/1024u>=UINT16_MAX)
            return fail(p);
        p->requested_kib[i]=(uint16_t)(used/1024u);
#else
        if(cold_hit || !warm_hit) return fail(p);
#endif
        if(!sample(before,mid,&p->cold_us[i]) ||
           !sample(mid,after,&p->warm_us[i]) ||
           memcmp(a,b,used)!=0) return fail(p);
        /* Independent reference, deliberately outside timing window. */
        foj_iso_render(&visual,b,width,height,width);
        if(memcmp(a,b,used)!=0)return fail(p);
    }
    if(p->cache.misses!=FOJ_BASE_SCALE_MODES ||
       p->cache.hits!=FOJ_BASE_SCALE_MODES ||
       p->cache.bypasses!=0)return fail(p);
#if FOJ_STAGE251_COMPACT
    if(p->cache.allocations!=FOJ_BASE_SCALE_MODES ||
       p->cache.releases!=FOJ_BASE_SCALE_MODES-1 ||
       p->cache.allocated_bytes!=(size_t)bytes[2])
        return fail(p);
#endif
    p->scene_key=*battle;
    p->preview=preview;
    p->key_valid=true;
    p->ready=true;
    return true;
}
bool foj_base_scale_draw(const FojBaseScaleProbe *p,uint32_t *pixels,
                         int width,int height,int stride) {
    if(!p || !pixels || width<FOJ_BASE_SCALE_STATUS_X+8 ||
       height<FOJ_BASE_SCALE_Y+8 || stride<width || stride<=0 ||
       height>INT_MAX/stride)return false;
    static const uint32_t cold_colors[FOJ_BASE_SCALE_MODES]={
        UINT32_C(0xff55d8b3),UINT32_C(0xff74bfed),UINT32_C(0xffbaacff)
    };
    static const uint32_t warm_colors[FOJ_BASE_SCALE_MODES]={
        UINT32_C(0xffedb853),UINT32_C(0xffed8ba7),UINT32_C(0xff68d0f5)
    };
    const uint32_t off=UINT32_C(0xff302530);
    const uint32_t pending=UINT32_C(0xffb28c51);
    const uint32_t error=UINT32_C(0xff2929f4);
    const uint32_t ready=UINT32_C(0xff54e394);
    for(int i=0;i<FOJ_BASE_SCALE_MODES;++i) {
        for(int arm=0;arm<2;++arm) {
            const int x0=FOJ_BASE_SCALE_FIRST_X+(i*2+arm)*72;
            const uint16_t value=arm ? p->warm_us[i]:p->cold_us[i];
            const uint32_t on=arm ? warm_colors[i]:cold_colors[i];
            for(int bit=0;bit<FOJ_BASE_SCALE_BITS;++bit) {
                const int x=x0+FOJ_BASE_SCALE_STEP*bit;
                const uint32_t color=!p->ready || p->failed ? pending:
                    (value & (UINT16_C(1)<<bit)) ? on:off;
                for(int yy=0;yy<8;++yy)
                    for(int xx=0;xx<3;++xx)
                        pixels[(FOJ_BASE_SCALE_Y+yy)*stride+x+xx]=color;
            }
        }
    }
    const uint32_t tile=p->failed ? error:p->ready ? ready:pending;
    for(int yy=0;yy<8;++yy)
        for(int xx=0;xx<8;++xx)
            pixels[(FOJ_BASE_SCALE_Y+yy)*stride+
                   FOJ_BASE_SCALE_STATUS_X+xx]=tile;
    return true;
}

#if FOJ_STAGE251_COMPACT
void foj_base_scale_release(FojBaseScaleProbe *p) {
    if(!p)return;
    foj_compact_base_release(&p->cache);
    p->ready=false;p->key_valid=false;
}
/* Three optical 16-bit KiB values, with an independent status tile. */
bool foj_base_scale_draw_memory(const FojBaseScaleProbe *p,
                                uint32_t *pixels,int width,int height,int stride) {
    if(!p || !pixels || width<FOJ_BASE_COMPACT_STATUS_X+8 ||
       height<FOJ_BASE_COMPACT_Y+8 || stride<width || stride<=0 ||
       height>INT_MAX/stride)return false;
    const uint32_t on[FOJ_BASE_SCALE_MODES]={
        UINT32_C(0xff59de8b),UINT32_C(0xffdd7848),UINT32_C(0xff76abec)
    };
    const uint32_t off=UINT32_C(0xff302530);
    const uint32_t pending=UINT32_C(0xffb28c51);
    for(int i=0;i<FOJ_BASE_SCALE_MODES;++i)
        for(int bit=0;bit<16;++bit) {
            const int x=FOJ_BASE_COMPACT_X+i*72+bit*4;
            const uint32_t pixel=(!p->ready || p->failed) ? pending :
                (p->requested_kib[i]&(UINT16_C(1)<<bit)) ? on[i]:off;
            for(int y=0;y<8;++y)
                for(int d=0;d<3;++d)
                    pixels[(FOJ_BASE_COMPACT_Y+y)*stride+x+d]=pixel;
        }
    const uint32_t tile=p->failed ? UINT32_C(0xff2929f4) :
        p->ready ? UINT32_C(0xff54e394):pending;
    for(int y=0;y<8;++y)
        for(int d=0;d<8;++d)
            pixels[(FOJ_BASE_COMPACT_Y+y)*stride+FOJ_BASE_COMPACT_STATUS_X+d]=tile;
    return true;
}
#endif
