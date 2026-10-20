/* Stage254: exact-sized Stage253 baseline versus 900-KiB bounded reuse.
 * Strictly host synthetic CPU tests, no PS3 content or physical RAM telemetry. */
#include "compact_reuse_probe.h"
#include <assert.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
enum {FRAME_PIXELS=1280*720};
static uint32_t *fresh(void) {
    uint32_t *p=(uint32_t *)calloc(FRAME_PIXELS,sizeof(uint32_t));
    assert(p);return p;
}
static void test_comparison(void) {
    uint32_t *a=fresh(),*b=fresh();
    FojCompactChurnReceipt baseline={0};
    FojReuseReceipt candidate={0};
    assert(!foj_reuse_probe_run(NULL,&baseline,a,b));
    assert(!foj_reuse_probe_run(&candidate,&baseline,a,b));
    assert(foj_compact_churn_run(&baseline,a,b));
    assert(!foj_reuse_probe_run(&candidate,&baseline,NULL,b));
    assert(!foj_reuse_probe_run(&candidate,&baseline,a,a));
    assert(baseline.allocations==48 && baseline.releases==48);
    for(int i=0;i<2;++i) {
        assert(foj_reuse_probe_run(&candidate,&baseline,a,b));
        assert(candidate.passed && candidate.frames==384);
        assert(candidate.exact_allocations==48);
        assert(candidate.reuse_allocations==32);
        assert(candidate.reuse_releases==32);
        assert(candidate.allocations_saved==16);
        assert(candidate.extra_small_kib==675);
    }
    const int w=985,h=106;
    uint32_t *frame=(uint32_t *)calloc((size_t)w*h,sizeof(uint32_t));
    assert(frame);
    assert(foj_reuse_probe_draw(&candidate,frame,w,h,w));
    assert(frame[FOJ_REUSE_Y*w+FOJ_REUSE_STATUS_X]==UINT32_C(0xff54e394));
    assert(foj_reuse_probe_draw(&candidate,frame,FOJ_REUSE_STATUS_X+8,
                                FOJ_REUSE_Y+8,w));
    assert(!foj_reuse_probe_draw(&candidate,frame,FOJ_REUSE_STATUS_X+7,h,w));
    assert(!foj_reuse_probe_draw(&candidate,frame,w,FOJ_REUSE_Y+7,w));
    assert(!foj_reuse_probe_draw(&candidate,frame,w,h,w-1));
    candidate.passed=false;
    assert(foj_reuse_probe_draw(&candidate,frame,w,h,w));
    assert(frame[FOJ_REUSE_Y*w+FOJ_REUSE_STATUS_X]==UINT32_C(0xff2929f4));
    free(frame);free(a);free(b);
}
static void test_capacity_budget_and_fail_closed(void) {
    FojCompactBaseCache c={0};
    foj_compact_base_init(&c);
    c.reuse_floor_bytes=900u*1024u;
    FojDemo scene;foj_demo_init(&scene);
    uint32_t *a=fresh(),*b=fresh();
    c.budget_bytes=230400;
    assert(foj_compact_base_draw(&c,&scene,a,320,180,320)==-1);
    assert(c.raster==NULL && c.allocated_bytes==0);
    c.budget_bytes=3600u*1024u;
    assert(foj_compact_base_draw(&c,&scene,a,320,180,320)==0);
    assert(c.allocated_bytes==900u*1024u && c.allocations==1);
    assert(foj_compact_base_draw(&c,&scene,b,320,180,320)==1);
    assert(memcmp(a,b,230400)==0);
    assert(foj_compact_base_draw(&c,&scene,a,640,360,640)==0);
    assert(c.allocated_bytes==900u*1024u && c.allocations==1);
    foj_iso_render(&scene,b,640,360,640);
    assert(memcmp(a,b,900u*1024u)==0);
    c.inject_fail_next_allocation=true;
    assert(foj_compact_base_draw(&c,&scene,a,1280,720,1280)==-1);
    assert(!c.inject_fail_next_allocation && !c.valid && !c.raster);
    assert(c.allocated_bytes==0 && c.releases==1);
    assert(foj_compact_base_draw(&c,&scene,a,1280,720,1280)==0);
    assert(c.allocated_bytes==3600u*1024u && c.allocations==2);
    assert(foj_compact_base_draw(&c,&scene,b,1280,720,1280)==1);
    assert(memcmp(a,b,3600u*1024u)==0);
    assert(foj_compact_base_draw(&c,&scene,a,320,180,320)==0);
    assert(c.allocated_bytes==900u*1024u && c.allocations==3);
    foj_iso_render(&scene,b,320,180,320);
    assert(memcmp(a,b,230400)==0);
    foj_compact_base_release(&c);
    assert(c.allocations==c.releases && !c.raster);
    free(a);free(b);
}
int main(void){test_comparison();test_capacity_budget_and_fail_closed();return 0;}
