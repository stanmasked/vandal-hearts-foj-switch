/* Stage255: budget-aware fallback for Stage254's synthetic CPU raster cache.
 * This is NOT a physical Nintendo Switch memory or game FPS benchmark. */
#include "base_cache_compact.h"
#include <assert.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>

#if !defined(FOJ_STAGE254_REUSE) || !FOJ_STAGE254_REUSE || \
    !defined(FOJ_STAGE255_BUDGET_FALLBACK) || !FOJ_STAGE255_BUDGET_FALLBACK
#error "Stage255 tests require both research-only opt-in flags"
#endif

enum { MAX_PIXELS=1280*720, SMALL_KIB=225, MEDIUM_KIB=900, LARGE_KIB=3600 };

static uint32_t *scratch(void) {
    uint32_t *p=(uint32_t *)calloc(MAX_PIXELS,sizeof(uint32_t));
    assert(p);
    return p;
}

static void check_frame(FojCompactBaseCache *c,FojDemo *scene,
                        uint32_t *pixels,uint32_t *oracle,
                        int w,int h,int expected_state,size_t capacity_kib) {
    assert(foj_compact_base_draw(c,scene,pixels,w,h,w)==expected_state);
    assert(c->valid && c->raster);
    assert(c->allocated_bytes==capacity_kib*1024u);
    assert(c->allocated_bytes<=c->budget_bytes);
    foj_iso_render(scene,oracle,w,h,w);
    assert(memcmp(pixels,oracle,(size_t)w*(size_t)h*sizeof(uint32_t))==0);
}

static void test_budget_fallback_and_recovery(void) {
    FojCompactBaseCache c={0};
    FojDemo scene;
    foj_demo_init(&scene);
    foj_compact_base_init(&c);
    c.reuse_floor_bytes=(size_t)MEDIUM_KIB*1024u;
    uint32_t *a=scratch(),*b=scratch();

    /* Strictly insufficient even for exact 320x180 frame. */
    c.budget_bytes=(SMALL_KIB-1u)*1024u;
    assert(foj_compact_base_draw(&c,&scene,a,320,180,320)==-1);
    assert(!c.valid && !c.raster && c.allocations==0);

    /* Stage254 floor is too expensive, but the active frame fits. */
    c.budget_bytes=SMALL_KIB*1024u;
    check_frame(&c,&scene,a,b,320,180,0,SMALL_KIB);
    check_frame(&c,&scene,a,b,320,180,1,SMALL_KIB);
    assert(c.allocations==1 && c.hits==1 && c.misses==1);

    /* Larger frame exceeds the budget: reject, free and invalidate. */
    assert(foj_compact_base_draw(&c,&scene,a,640,360,640)==-1);
    assert(!c.raster && !c.valid && c.allocated_bytes==0);
    assert(c.releases==1);
    check_frame(&c,&scene,a,b,320,180,0,SMALL_KIB);

    /* The small frame still reuses its exact-sized allocation below floor. */
    c.budget_bytes=500u*1024u;
    scene.cursor_x=1;
    check_frame(&c,&scene,a,b,320,180,0,SMALL_KIB);
    check_frame(&c,&scene,a,b,320,180,1,SMALL_KIB);
    assert(c.allocations==2);

    /* At 900 KiB, the Stage254 shared-capacity policy applies unchanged. */
    c.budget_bytes=MEDIUM_KIB*1024u;
    check_frame(&c,&scene,a,b,320,180,0,MEDIUM_KIB);
    const uint64_t before=c.allocations;
    check_frame(&c,&scene,a,b,640,360,0,MEDIUM_KIB);
    check_frame(&c,&scene,a,b,640,360,1,MEDIUM_KIB);
    assert(c.allocations==before);

    /* Reducing the budget shrinks the old allocation before a small frame. */
    c.budget_bytes=SMALL_KIB*1024u;
    check_frame(&c,&scene,a,b,320,180,0,SMALL_KIB);
    assert(c.allocated_bytes==SMALL_KIB*1024u);

    /* Reducing below the used frame size must release old storage. */
    c.budget_bytes=(SMALL_KIB-1u)*1024u;
    assert(foj_compact_base_draw(&c,&scene,a,320,180,320)==-1);
    assert(!c.raster && !c.valid && c.allocated_bytes==0);

    /* Large frame still gets exactly 3600 KiB when budget allows it. */
    c.budget_bytes=LARGE_KIB*1024u;
    check_frame(&c,&scene,a,b,1280,720,0,LARGE_KIB);
    check_frame(&c,&scene,a,b,1280,720,1,LARGE_KIB);

    /* Fault injection must not leave a stale high-resolution raster. */
    c.budget_bytes=SMALL_KIB*1024u;
    c.inject_fail_next_allocation=true;
    assert(foj_compact_base_draw(&c,&scene,a,320,180,320)==-1);
    assert(!c.inject_fail_next_allocation);
    assert(!c.raster && !c.valid && c.allocated_bytes==0);
    check_frame(&c,&scene,a,b,320,180,0,SMALL_KIB);

    /* The policy never changes frame contents or leaves heap storage live. */
    foj_compact_base_release(&c);
    assert(!c.raster && !c.valid && !c.allocated_bytes);
    assert(c.allocations==c.releases);
    assert(c.bypasses==0);
    free(a);
    free(b);
}

static void test_strided_and_invalid_inputs(void) {
    FojCompactBaseCache c={0};
    foj_compact_base_init(&c);
    c.reuse_floor_bytes=MEDIUM_KIB*1024u;
    c.budget_bytes=SMALL_KIB*1024u;
    FojDemo scene;
    foj_demo_init(&scene);
    uint32_t *a=scratch(),*b=scratch();
    for(int y=0;y<180;++y)
        for(int d=0;d<2;++d)
            a[(size_t)y*322u+320u+(size_t)d]=UINT32_C(0xdeadbeef);
    assert(foj_compact_base_draw(&c,&scene,a,320,180,322)==0);
    assert(foj_compact_base_draw(&c,&scene,b,320,180,320)==1);
    foj_iso_render(&scene,b,320,180,320);
    for(int y=0;y<180;++y) {
        assert(memcmp(a+(size_t)y*322u,b+(size_t)y*320u,320u*sizeof(uint32_t))==0);
        assert(a[(size_t)y*322u+320u]==UINT32_C(0xdeadbeef));
        assert(a[(size_t)y*322u+321u]==UINT32_C(0xdeadbeef));
    }
    assert(foj_compact_base_draw(&c,&scene,a,320,180,319)==-1);
    assert(foj_compact_base_draw(&c,&scene,a,0,180,322)==-1);
    assert(foj_compact_base_draw(&c,&scene,a,1281,720,1281)==-1);
    foj_compact_base_release(&c);
    assert(c.allocations==c.releases);
    free(a);
    free(b);
}

int main(void) {
    test_budget_fallback_and_recovery();
    test_strided_and_invalid_inputs();
    return 0;
}
