/* Stage250: validate three resolution sweeps, parity, counters and fail closed. */
#include "base_cache_scale_probe.h"
#include "base_cache_stability_probe.h"
#include <assert.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
enum {MAX_PIXELS=1280*720};
typedef struct {uint64_t t,step;} Clock;
static uint64_t tick(void *ctx) {
    Clock *p=(Clock *)ctx;p->t+=p->step;return p->t;
}
static uint64_t frozen(void *ctx) {(void)ctx;return UINT64_C(7);}
static FojBaseScaleProbe *probe_new(void) {
    FojBaseScaleProbe *p=calloc(1,sizeof(*p));assert(p);
    foj_base_scale_init(p);return p;
}
static uint32_t *frame_new(void) {
    uint32_t *p=calloc(MAX_PIXELS,sizeof(uint32_t));assert(p);return p;
}
static void test_sizes_and_scene_keys(void) {
    FojBaseScaleProbe *p=probe_new();
    FojBattle battle;foj_battle_init(&battle);
    const FojBattle original=battle;
    uint32_t *a=frame_new(),*b=frame_new();
    Clock clock={0,UINT64_C(1000000)};
    assert(foj_base_scale_step(p,&battle,true,a,b,tick,&clock));
    assert(p->ready && !p->failed && p->scene_resets==1);
    assert(p->cache.hits==3 && p->cache.misses==3);
    assert(p->cache.width==1280 && p->cache.height==720);
    assert(p->active_bytes[0]==230400 && p->active_bytes[1]==921600 &&
           p->active_bytes[2]==3686400);
    for(int i=0;i<FOJ_BASE_SCALE_MODES;++i)
        assert(p->cold_us[i]==1000 && p->warm_us[i]==1000);
    assert(memcmp(&battle,&original,sizeof(battle))==0);
    const uint64_t last=clock.t;
    assert(foj_base_scale_step(p,&battle,true,a,b,tick,&clock));
    assert(clock.t==last); /* Unchanged state: no synthetic extra work. */
    battle.map.cells[0][0].elevation++;
    assert(foj_base_scale_step(p,&battle,true,a,b,tick,&clock));
    assert(p->scene_resets==2 && p->cache.hits==3 &&
           p->cache.misses==3);
    assert(foj_base_scale_step(p,&battle,false,a,b,tick,&clock));
    assert(p->scene_resets==3);
    const int sw=980,sh=40;
    uint32_t *screen=calloc((size_t)sw*sh,sizeof(uint32_t));
    assert(screen);
    assert(foj_base_scale_draw(p,screen,sw,sh,sw));
    assert(screen[FOJ_BASE_SCALE_Y*sw+FOJ_BASE_SCALE_STATUS_X]==
           UINT32_C(0xff54e394));
    assert(!foj_base_scale_draw(p,screen,sw-1,sh,sw));
    assert(!foj_base_scale_draw(p,screen,sw,sh-1,sw));
    assert(!foj_base_scale_draw(p,screen,sw,sh,sw-1));
    free(screen);free(a);free(b);free(p);
}
static void test_fail_closed(void) {
    FojBaseScaleProbe *p=probe_new();
    FojBattle battle;foj_battle_init(&battle);
    uint32_t *a=frame_new(),*b=frame_new();
    Clock clock={0,UINT64_C(1000000)};
    assert(!foj_base_scale_step(NULL,&battle,true,a,b,tick,&clock));
    assert(!foj_base_scale_step(p,NULL,true,a,b,tick,&clock));
    assert(!foj_base_scale_step(p,&battle,true,NULL,b,tick,&clock));
    assert(!foj_base_scale_step(p,&battle,true,a,a,tick,&clock));
    assert(!foj_base_scale_step(p,&battle,true,a,b,NULL,NULL));
    assert(!foj_base_scale_step(p,&battle,true,a,b,frozen,NULL));
    assert(p->failed && !p->ready);
    assert(!foj_base_scale_step(p,&battle,true,a,b,tick,&clock));
    foj_base_scale_init(p);
    clock.step=UINT64_C(70000000);
    assert(!foj_base_scale_step(p,&battle,true,a,b,tick,&clock));
    assert(p->failed);
    const int sw=980,sh=40;
    uint32_t *screen=calloc((size_t)sw*sh,sizeof(uint32_t));
    assert(screen);
    assert(foj_base_scale_draw(p,screen,sw,sh,sw));
    assert(screen[FOJ_BASE_SCALE_Y*sw+FOJ_BASE_SCALE_STATUS_X]==
           UINT32_C(0xff2929f4));
    /* Explicit accounting includes opt-in static caches and two
     * full-resolution RGBA scratch frames, not Switch FB/system RAM. */
    const size_t known_bytes=sizeof(FojBaseScaleProbe)+
        sizeof(FojBaseStabilityProbe)+sizeof(FojIsoBaseCache)+
        2*(size_t)MAX_PIXELS*sizeof(uint32_t);
    assert(known_bytes<(size_t)21*1024*1024);
    free(screen);free(a);free(b);free(p);
}
int main(void){test_sizes_and_scene_keys();test_fail_closed();return 0;}
