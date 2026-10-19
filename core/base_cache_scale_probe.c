/* Stage250: controlled cross-resolution cold/warm CPU raster measurements. */
#include "base_cache_scale_probe.h"
#include <limits.h>
#include <stddef.h>
#include <string.h>

static const int modes[FOJ_BASE_SCALE_MODES][2]={
    {320,180},{640,360},{1280,720}
};
static const uint32_t bytes[FOJ_BASE_SCALE_MODES]={
    UINT32_C(230400),UINT32_C(921600),UINT32_C(3686400)
};
void foj_base_scale_init(FojBaseScaleProbe *p) {
    if(!p)return;
    foj_iso_base_cache_init(&p->cache);
    for(int i=0;i<FOJ_BASE_SCALE_MODES;++i) {
        p->cold_us[i]=p->warm_us[i]=0;
        p->active_bytes[i]=bytes[i];
    }
    p->scene_resets=0;
    p->key_valid=p->preview=p->ready=p->failed=false;
}
static bool fail(FojBaseScaleProbe *p) {
    p->failed=true;
    p->ready=false;
    return false;
}
/* Compare gameplay-relevant members, never struct padding or an
 * uninitialised padding byte from a caller-owned battle snapshot. Scene
 * invalidation must reflect an actual generated battle state change. */
static bool same_battle_state(const FojBattle *a,const FojBattle *b) {
    const FojDemo *x=&a->map,*y=&b->map;
    if(x->hero_x!=y->hero_x || x->hero_y!=y->hero_y ||
       x->enemy_x!=y->enemy_x || x->enemy_y!=y->enemy_y ||
       x->cursor_x!=y->cursor_x || x->cursor_y!=y->cursor_y ||
       x->selected!=y->selected ||
       a->hero_hp!=b->hero_hp || a->enemy_hp!=b->enemy_hp ||
       a->moved_this_turn!=b->moved_this_turn ||
       a->previous_hero_x!=b->previous_hero_x ||
       a->previous_hero_y!=b->previous_hero_y ||
       a->attacked_this_turn!=b->attacked_this_turn ||
       a->guarded_this_turn!=b->guarded_this_turn ||
       a->turn_number!=b->turn_number || a->outcome!=b->outcome)
        return false;
    for(int row=0;row<FOJ_HEIGHT;++row)
        for(int col=0;col<FOJ_WIDTH;++col)
            if(x->cells[row][col].elevation!=y->cells[row][col].elevation ||
               x->cells[row][col].blocked!=y->cells[row][col].blocked)
                return false;
    return true;
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
                       !same_battle_state(&p->scene_key,battle);
    if(!changed) return p->ready;
    if(p->scene_resets==UINT32_MAX)return fail(p);
    ++p->scene_resets;
    p->ready=false;
    p->key_valid=false;
    foj_iso_base_cache_init(&p->cache);
    FojDemo visual=battle->map;
    if(battle->enemy_hp==0) {
        visual.enemy_x=-1;
        visual.enemy_y=-1;
    }
    for(int i=0;i<FOJ_BASE_SCALE_MODES;++i) {
        const int width=modes[i][0],height=modes[i][1];
        const size_t used=(size_t)width*(size_t)height*sizeof(uint32_t);
        const uint64_t before=clock_ns(ctx);
        const bool cold_hit=foj_iso_base_cache_draw(
            &p->cache,&visual,a,width,height,width);
        const uint64_t mid=clock_ns(ctx);
        const bool warm_hit=foj_iso_base_cache_draw(
            &p->cache,&visual,b,width,height,width);
        const uint64_t after=clock_ns(ctx);
        if(cold_hit || !warm_hit || !sample(before,mid,&p->cold_us[i]) ||
           !sample(mid,after,&p->warm_us[i]) ||
           memcmp(a,b,used)!=0) return fail(p);
        /* Independent reference, deliberately outside timing window. */
        foj_iso_render(&visual,b,width,height,width);
        if(memcmp(a,b,used)!=0)return fail(p);
    }
    if(p->cache.misses!=FOJ_BASE_SCALE_MODES ||
       p->cache.hits!=FOJ_BASE_SCALE_MODES ||
       p->cache.bypasses!=0)return fail(p);
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
