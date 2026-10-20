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
    /* foj_demo_init() already sets cursor_x to 1. Move it for real:
     * an unchanged scene must be a HIT, not a fabricated cold MISS. */
    const int old_cursor_x=scene.cursor_x;
    scene.cursor_x=(old_cursor_x+1)%FOJ_WIDTH;
    assert(scene.cursor_x!=old_cursor_x);
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

/* A 384-frame version of the Stage253 scene/resolution schedule.
 * Here each block's budget is exactly its frame payload, so the opt-in
 * fallback must retain pixel parity without falsely promising that it
 * also preserves Stage254's 32-allocation optimization. */
static void test_384_frame_tight_budget(void) {
    static const int widths[3]={320,640,1280};
    static const int heights[3]={180,360,720};
    FojCompactBaseCache c={0};
    foj_compact_base_init(&c);
    c.reuse_floor_bytes=MEDIUM_KIB*1024u;
    uint32_t *a=scratch(),*b=scratch();
    for(int n=0;n<384;++n) {
        const int block=n/8;
        const int mode=block%3;
        const int w=widths[mode],h=heights[mode];
        const int variant=(n%8)/2;
        FojDemo scene;
        foj_demo_init(&scene);
        scene.cursor_x=variant;
        scene.cursor_y=block%FOJ_HEIGHT;
        scene.cells[0][0].elevation=(uint8_t)variant;
        const size_t used=(size_t)w*(size_t)h*sizeof(uint32_t);
        c.budget_bytes=used;
        const uint64_t allocations_before=c.allocations;
        check_frame(&c,&scene,a,b,w,h,n%2==0?0:1,used/1024u);
        if(n%8==0)
            assert(c.allocations==allocations_before+1u);
        else
            assert(c.allocations==allocations_before);
    }
    assert(c.hits==192 && c.misses==192 && c.bypasses==0);
    assert(c.allocations==48 && c.releases==47);
    foj_compact_base_release(&c);
    assert(c.allocations==c.releases && !c.raster && !c.valid);
    free(a);
    free(b);
}

/* Probe the exact byte either side of the 225, 900 and 3600 KiB
 * boundaries. This is independent of any host allocator fragmentation
 * or the Nintendo Switch's physical memory accounting. */
static void test_budget_byte_boundaries(void) {
    static const int widths[]={320,640,1280};
    static const int heights[]={180,360,720};
    static const size_t budgets[]={
        0u,
        (size_t)SMALL_KIB*1024u-1u,
        (size_t)SMALL_KIB*1024u,
        (size_t)SMALL_KIB*1024u+1u,
        (size_t)MEDIUM_KIB*1024u-1u,
        (size_t)MEDIUM_KIB*1024u,
        (size_t)MEDIUM_KIB*1024u+1u,
        (size_t)LARGE_KIB*1024u-1u,
        (size_t)LARGE_KIB*1024u
    };
    uint32_t *pixels=scratch(),*oracle=scratch();
    FojDemo scene;
    foj_demo_init(&scene);
    for(int mode=0;mode<3;++mode) {
        const int w=widths[mode],h=heights[mode];
        const size_t used=(size_t)w*(size_t)h*sizeof(uint32_t);
        const size_t floor=(size_t)MEDIUM_KIB*1024u;
        const size_t preferred=used>floor?used:floor;
        for(size_t i=0;i<sizeof(budgets)/sizeof(budgets[0]);++i) {
            FojCompactBaseCache c={0};
            foj_compact_base_init(&c);
            c.reuse_floor_bytes=floor;
            c.budget_bytes=budgets[i];
            const bool allowed=used<=budgets[i];
            const size_t expected_capacity=preferred<=budgets[i]?
                                           preferred:used;
            if(allowed) {
                assert(foj_compact_base_draw(&c,&scene,pixels,w,h,w)==0);
                assert(c.allocated_bytes==expected_capacity);
                foj_iso_render(&scene,oracle,w,h,w);
                assert(memcmp(pixels,oracle,used)==0);
                assert(foj_compact_base_draw(&c,&scene,pixels,w,h,w)==1);
                assert(c.allocations==1 && c.hits==1 && c.misses==1);
            } else {
                assert(foj_compact_base_draw(&c,&scene,pixels,w,h,w)==-1);
                assert(!c.raster && !c.valid && c.allocated_bytes==0);
                assert(c.allocations==0 && c.hits==0 && c.misses==0);
            }
            foj_compact_base_release(&c);
            assert(c.allocations==c.releases && !c.raster);
        }
    }
    free(pixels);
    free(oracle);
}

int main(void) {
    test_budget_fallback_and_recovery();
    test_strided_and_invalid_inputs();
    test_384_frame_tight_budget();
    test_budget_byte_boundaries();
    return 0;
}
