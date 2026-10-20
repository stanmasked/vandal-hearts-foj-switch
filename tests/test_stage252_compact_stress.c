/* Stage252 strict 96-cycle heap/scene endurance with deterministic OOM. */
#include "compact_stress_probe.h"
#include <assert.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>

enum { PIXELS=1280*720 };
static uint32_t *frame(void) {
    uint32_t *p=(uint32_t *)calloc(PIXELS,sizeof(uint32_t));
    assert(p);return p;
}
static void stress_receipt(void) {
    uint32_t *a=frame(),*b=frame();
    FojCompactStressReceipt r={0};
    assert(!foj_compact_stress_run(NULL,a,b));
    assert(!foj_compact_stress_run(&r,NULL,b));
    assert(!foj_compact_stress_run(&r,a,a));
    assert(foj_compact_stress_run(&r,a,b));
    assert(r.passed && r.cycles==96 && r.injected_failures==8);
    assert(r.allocations==96 && r.releases==96 && r.peak_kib==3600);
    /* Repeated stress with no process restart; ASan/LSan checks lifetimes. */
    assert(foj_compact_stress_run(&r,a,b));
    assert(r.passed && r.allocations==r.releases);
    const int w=850,h=72;
    uint32_t *screen=(uint32_t *)calloc((size_t)w*h,sizeof(uint32_t));
    assert(screen);
    assert(foj_compact_stress_draw(&r,screen,w,h,w));
    assert(screen[FOJ_COMPACT_STRESS_Y*w+
                  FOJ_COMPACT_STRESS_STATUS_X]==UINT32_C(0xff54e394));
    assert(foj_compact_stress_draw(&r,screen,
           FOJ_COMPACT_STRESS_STATUS_X+8,FOJ_COMPACT_STRESS_Y+8,w));
    assert(!foj_compact_stress_draw(&r,screen,
            FOJ_COMPACT_STRESS_STATUS_X+7,h,w));
    assert(!foj_compact_stress_draw(&r,screen,w,
            FOJ_COMPACT_STRESS_Y+7,w));
    r.passed=false;
    assert(foj_compact_stress_draw(&r,screen,w,h,w));
    assert(screen[FOJ_COMPACT_STRESS_Y*w+
                  FOJ_COMPACT_STRESS_STATUS_X]==UINT32_C(0xff2929f4));
    free(screen);free(a);free(b);
}
static void fail_then_recover(void) {
    FojCompactBaseCache cache={0};
    foj_compact_base_init(&cache);
    FojDemo scene;foj_demo_init(&scene);
    uint32_t *a=frame(),*b=frame();
    assert(foj_compact_base_draw(&cache,&scene,a,320,180,320)==0);
    assert(foj_compact_base_draw(&cache,&scene,b,320,180,320)==1);
    assert(memcmp(a,b,230400)==0);
    cache.inject_fail_next_allocation=true;
    assert(foj_compact_base_draw(&cache,&scene,a,640,360,640)==-1);
    assert(!cache.inject_fail_next_allocation && !cache.valid);
    assert(!cache.raster && cache.allocated_bytes==0);
    assert(foj_compact_base_draw(&cache,&scene,a,640,360,640)==0);
    assert(cache.allocated_bytes==921600);
    assert(foj_compact_base_draw(&cache,&scene,b,640,360,640)==1);
    foj_iso_render(&scene,b,640,360,640);
    assert(memcmp(a,b,921600)==0);
    cache.budget_bytes=100;
    assert(foj_compact_base_draw(&cache,&scene,a,1280,720,1280)==-1);
    /* Budget rejection must not make previous valid cached raster stale. */
    assert(cache.allocated_bytes==921600 && cache.valid);
    assert(foj_compact_base_draw(&cache,&scene,b,640,360,640)==-1);
    cache.budget_bytes=3686400;
    assert(foj_compact_base_draw(&cache,&scene,b,640,360,640)==1);
    assert(cache.allocations==2 && cache.releases==1);
    foj_compact_base_release(&cache);
    assert(cache.allocations==cache.releases);
    free(a);free(b);
}
int main(void){stress_receipt();fail_then_recover();return 0;}
