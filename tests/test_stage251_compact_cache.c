/* Stage251: independent compact CPU cache and experiment guest lifecycle. */
#include "base_cache_scale_probe.h"
#include "base_cache_compact.h"
#include <assert.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>

enum { MAXPIX=1280*720 };
typedef struct {uint64_t ns,step;} Clock;
static uint64_t tick(void *ctx) {
    Clock *clock=(Clock *)ctx;
    clock->ns+=clock->step;
    return clock->ns;
}
static uint32_t *pixels(void) {
    uint32_t *p=(uint32_t *)calloc(MAXPIX+5000,sizeof(uint32_t));
    assert(p);return p;
}
static void test_exact_heap_storage(void) {
    FojCompactBaseCache c={0};
    foj_compact_base_init(&c);
    FojDemo scene;foj_demo_init(&scene);
    uint32_t *a=pixels(),*b=pixels();
    const int widths[]={320,640,1280},heights[]={180,360,720};
    for(int mode=0;mode<3;++mode) {
        int w=widths[mode],h=heights[mode];
        size_t bytes=(size_t)w*h*sizeof(uint32_t);
        assert(foj_compact_base_draw(&c,&scene,a,w,h,w)==0);
        assert(c.allocated_bytes==bytes && c.valid && c.width==w);
        assert(foj_compact_base_draw(&c,&scene,b,w,h,w)==1);
        assert(memcmp(a,b,bytes)==0);
        foj_iso_render(&scene,b,w,h,w);
        assert(memcmp(a,b,bytes)==0);
    }
    assert(c.allocations==3 && c.releases==2 && c.hits==3 &&
           c.misses==3 && c.bypasses==0);
    /* Same dimension and changed terrain should MISS without reallocation. */
    scene.cells[0][0].elevation++;
    assert(foj_compact_base_draw(&c,&scene,a,1280,720,1280)==0);
    assert(c.allocations==3 && c.misses==4);
    assert(foj_compact_base_draw(&c,&scene,b,1280,720,1280)==1);
    foj_compact_base_reset(&c);
    assert(!c.raster && !c.valid && c.allocated_bytes==0);
    assert(c.allocations==0 && c.releases==0);
    /* Shrink starts from zero and reserves only 320x180, not 1280x720. */
    assert(foj_compact_base_draw(&c,&scene,a,320,180,320)==0);
    assert(c.allocated_bytes==230400 && c.allocations==1);
    foj_compact_base_release(&c);
    assert(c.raster==NULL && c.allocated_bytes==0);
    free(a);free(b);
}
static void test_stride_fail_and_budget(void) {
    FojCompactBaseCache c={0};
    foj_compact_base_init(&c);
    FojDemo scene;foj_demo_init(&scene);
    uint32_t *a=pixels(),*b=pixels();
    for(int y=0;y<180;++y)
        for(int dx=0;dx<2;++dx)
            a[y*322+320+dx]=UINT32_C(0xdeadbeef);
    assert(foj_compact_base_draw(&c,&scene,a,320,180,322)==0);
    assert(foj_compact_base_draw(&c,&scene,b,320,180,322)==1);
    for(int y=0;y<180;++y)
        for(int dx=0;dx<2;++dx)
            assert(a[y*322+320+dx]==UINT32_C(0xdeadbeef));
    assert(foj_compact_base_draw(&c,&scene,a,0,180,322)==-1);
    assert(foj_compact_base_draw(&c,&scene,a,1281,720,1281)==-1);
    assert(foj_compact_base_draw(&c,&scene,a,320,180,319)==-1);
    assert(foj_compact_base_draw(&c,&scene,a,320,180,0)==-1);
    assert(foj_compact_base_draw(NULL,&scene,a,320,180,320)==-1);
    assert(foj_compact_base_draw(&c,NULL,a,320,180,320)==-1);
    c.budget_bytes=1024;
    /* Fail-closed on a requested allocation over the experiment budget. */
    assert(foj_compact_base_draw(&c,&scene,a,640,360,640)==-1);
    foj_compact_base_release(&c);
    assert(!c.raster && !c.valid);
    free(a);free(b);
}
static void test_guest_probe_and_optical(void) {
    FojBaseScaleProbe *p=(FojBaseScaleProbe *)calloc(1,sizeof(*p));
    assert(p);foj_base_scale_init(p);
    assert(sizeof(*p)<4096);
    FojBattle battle;foj_battle_init(&battle);
    uint32_t *a=pixels(),*b=pixels();
    Clock clock={0,UINT64_C(1000000)};
    assert(foj_base_scale_step(p,&battle,true,a,b,tick,&clock));
    assert(p->ready && !p->failed && p->cache.allocations==3);
    assert(p->cache.releases==2 && p->cache.allocated_bytes==3686400);
    assert(p->requested_kib[0]==225 && p->requested_kib[1]==900 &&
           p->requested_kib[2]==3600);
    uint64_t unchanged=clock.ns;
    assert(foj_base_scale_step(p,&battle,true,a,b,tick,&clock));
    assert(clock.ns==unchanged);
    const int w=800,h=56;
    uint32_t *screen=(uint32_t *)calloc((size_t)w*h,sizeof(uint32_t));
    assert(screen && foj_base_scale_draw_memory(p,screen,w,h,w));
    assert(screen[FOJ_BASE_COMPACT_Y*w+FOJ_BASE_COMPACT_STATUS_X]==
           UINT32_C(0xff54e394));
    assert(!foj_base_scale_draw_memory(p,screen,759,h,w));
    assert(!foj_base_scale_draw_memory(p,screen,w,51,w));
    battle.map.cursor_x++;
    assert(foj_base_scale_step(p,&battle,true,a,b,tick,&clock));
    assert(p->scene_resets==2 && p->cache.allocations==3);
    foj_base_scale_release(p);
    assert(!p->cache.raster && p->cache.allocated_bytes==0);
    foj_base_scale_init(p);
    p->cache.budget_bytes=1024;
    assert(!foj_base_scale_step(p,&battle,true,a,b,tick,&clock));
    assert(p->failed && !p->ready && p->cache.raster==NULL);
    assert(!foj_base_scale_step(p,&battle,true,a,b,tick,&clock));
    assert(foj_base_scale_draw_memory(p,screen,w,h,w));
    assert(screen[FOJ_BASE_COMPACT_Y*w+FOJ_BASE_COMPACT_STATUS_X]==
           UINT32_C(0xff2929f4));
    free(screen);free(a);free(b);free(p);
}
int main(void) {
    test_exact_heap_storage();
    test_stride_fail_and_budget();
    test_guest_probe_and_optical();
    return 0;
}
