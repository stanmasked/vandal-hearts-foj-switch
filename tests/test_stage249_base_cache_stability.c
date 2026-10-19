/* Stage249: deterministic host clock only. No host FPS or GPU claims. */
#include "base_cache_stability_probe.h"
#include <assert.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
enum {W=320,H=180,N=W*H};
typedef struct {uint64_t stamp,step;} Clock;
static uint64_t tick(void *ctx) {
    Clock *c=(Clock *)ctx;
    c->stamp+=c->step;
    return c->stamp;
}
static uint64_t frozen(void *ctx) {(void)ctx;return UINT64_C(99);}
static FojBaseStabilityProbe *new_probe(void) {
    FojBaseStabilityProbe *p=calloc(1,sizeof(*p));
    assert(p); foj_base_stability_init(p);
    return p;
}
static uint32_t *new_frame(void) {
    uint32_t *frame=calloc(N,sizeof(*frame));
    assert(frame);return frame;
}
static void one(FojBaseStabilityProbe *p,FojBattle *battle,
                uint32_t *a,uint32_t *b,Clock *clock,bool preview) {
    assert(foj_base_stability_step(
        p,battle,preview,a,b,W,H,W,tick,clock));
    assert(memcmp(a,b,N*sizeof(uint32_t))==0);
}
static void test_three_real_windows_and_restarts(void) {
    FojBaseStabilityProbe *p=new_probe();
    FojBattle battle;foj_battle_init(&battle);
    assert(foj_battle_confirm(&battle)==FOJ_BATTLE_SELECTED);
    const FojBattle original=battle;
    uint32_t *a=new_frame(),*b=new_frame();
    Clock clock={0,UINT64_C(1000000)};
    for(int i=0;i<FOJ_BASE_PAIR_WINDOW*2;++i)
        one(p,&battle,a,b,&clock,true);
    assert(!p->ready && p->observed_windows==2);
    assert(p->cold_refill_us==1000 && p->warm_copy_us==1000);
    for(int i=0;i<FOJ_BASE_PAIR_WINDOW;++i)
        one(p,&battle,a,b,&clock,true);
    assert(p->ready && !p->failed && p->cold_valid);
    assert(p->observed_windows==3 && p->pair.completed_windows==3);
    assert(p->worst_window_spread_us==0);
    assert(p->cached_min_us==1000 && p->cached_max_us==1000);
    assert(p->uncached_min_us==1000 && p->uncached_max_us==1000);
    assert(p->scene_resets==1);
    assert(memcmp(&battle,&original,sizeof(battle))==0);
    /* Cursor and forecast toggles each invalidate ALL accumulated windows. */
    foj_battle_move_cursor(&battle,1,0);
    one(p,&battle,a,b,&clock,true);
    assert(!p->ready && p->observed_windows==0);
    assert(p->scene_resets==2 && p->pair.total_pairs==1);
    one(p,&battle,a,b,&clock,false);
    assert(p->scene_resets==3 && p->observed_windows==0);
    assert(p->pair.total_pairs==1);
    /* Every completed 32-pair mean contributes to min/max spread. */
    for(int i=1;i<FOJ_BASE_PAIR_WINDOW;++i)
        one(p,&battle,a,b,&clock,false);
    clock.step=UINT64_C(1500000);
    for(int i=0;i<FOJ_BASE_PAIR_WINDOW;++i)
        one(p,&battle,a,b,&clock,false);
    clock.step=UINT64_C(2000000);
    for(int i=0;i<FOJ_BASE_PAIR_WINDOW;++i)
        one(p,&battle,a,b,&clock,false);
    assert(p->ready && p->observed_windows==3);
    assert(p->cached_min_us==1000 && p->cached_max_us==2000);
    assert(p->uncached_min_us==1000 && p->uncached_max_us==2000);
    assert(p->worst_window_spread_us==1000);
    free(a);free(b);free(p);
}
static void test_fail_closed_and_visible_receipts(void) {
    FojBaseStabilityProbe *p=new_probe();
    FojBattle battle;foj_battle_init(&battle);
    uint32_t *a=new_frame(),*b=new_frame();
    Clock clock={0,UINT64_C(1000000)};
    assert(!foj_base_stability_step(p,&battle,true,a,b,W,H,W,frozen,NULL));
    assert(p->failed && !p->ready);
    assert(!foj_base_stability_step(p,&battle,true,a,b,W,H,W,tick,&clock));
    const int sw=760,sh=20;
    uint32_t *screen=calloc((size_t)sw*sh,sizeof(*screen));
    assert(screen);
    assert(foj_base_stability_draw(p,screen,sw,sh,sw));
    assert(screen[FOJ_BASE_STABILITY_Y*sw+FOJ_BASE_STABILITY_STATUS_X] ==
           UINT32_C(0xff2929f4));
    assert(!foj_base_stability_draw(p,screen,sw-1,sh,sw));
    assert(!foj_base_stability_draw(p,screen,sw,sh-1,sw));
    assert(!foj_base_stability_draw(p,screen,sw,sh,sw-1));
    assert(!foj_base_stability_draw(p,NULL,sw,sh,sw));
    foj_base_stability_init(p);
    assert(!foj_base_stability_step(p,&battle,true,a,a,W,H,W,tick,&clock));
    assert(!foj_base_stability_step(p,&battle,true,a,b,W,H,W+1,tick,&clock));
    assert(!foj_base_stability_step(p,&battle,true,a,b,W,0,W,tick,&clock));
    assert(!foj_base_stability_step(NULL,&battle,true,a,b,W,H,W,tick,&clock));
    assert(!foj_base_stability_step(p,&battle,true,a,b,W,H,W,NULL,NULL));
    assert(!foj_base_stability_step(p,&battle,true,a,b,
        FOJ_ISO_BASE_CACHE_WIDTH+1,H,FOJ_ISO_BASE_CACHE_WIDTH+1,
        tick,&clock));
    /* Buffer and storage audit for the opt-in 1280x720 research NRO.
     * Includes visible Stage247 raster, private Stage249 cache and both
     * scratch frames; other normal program/global data is not counted. */
    const size_t pixels=(size_t)FOJ_ISO_BASE_CACHE_WIDTH*
                        (size_t)FOJ_ISO_BASE_CACHE_HEIGHT;
    const size_t opt_in_static=sizeof(FojBaseStabilityProbe)+
        sizeof(FojIsoBaseCache)+2*pixels*sizeof(uint32_t);
    assert(opt_in_static < (size_t)17*1024*1024);
    free(screen);free(a);free(b);free(p);
}
int main(void) {
    test_three_real_windows_and_restarts();
    test_fail_closed_and_visible_receipts();
    return EXIT_SUCCESS;
}
