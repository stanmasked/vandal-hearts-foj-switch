/* Stage247: synthetic scene-exact base cache, never PS3 assets/GPU. */
#include "isometric_demo.h"
#include "isometric_base_cache.h"
#include <assert.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>

enum { W=320,H=180,STRIDE=W+7 };
static FojIsoBaseCache cache; /* 3.52 MiB: intentionally never on stack. */

static uint32_t *frame(void) {
    uint32_t *p=malloc((size_t)STRIDE*H*sizeof(uint32_t));
    assert(p);
    for(size_t i=0;i<(size_t)STRIDE*H;++i)
        p[i]=UINT32_C(0x3456789a);
    return p;
}
static void parity(const uint32_t *a,const uint32_t *b) {
    for(int y=0;y<H;++y) {
        assert(!memcmp(a+(size_t)y*STRIDE,b+(size_t)y*STRIDE,
                       (size_t)W*sizeof(uint32_t)));
        for(int x=W;x<STRIDE;++x) {
            assert(a[(size_t)y*STRIDE+x]==UINT32_C(0x3456789a));
            assert(b[(size_t)y*STRIDE+x]==UINT32_C(0x3456789a));
        }
    }
}
static void check(FojBattle *battle,bool show,bool expected_hit) {
    uint32_t *cached=frame(),*original=frame();
    FojBattle unchanged=*battle;
    FojBattleThreatCache a,b;
    foj_battle_threat_cache_init(&a);
    foj_battle_threat_cache_init(&b);
    bool hit=!expected_hit;
    FojIsoPhaseReceipt profile;
    foj_iso_render_battle_profiled_base_cached(
        battle,cached,W,H,STRIDE,show,&a,&cache,&hit,
        NULL,NULL,&profile);
    foj_iso_render_battle_cached_options(
        battle,original,W,H,STRIDE,show,&b);
    assert(hit==expected_hit);
    assert(!profile.valid); /* no clock callback means no false receipt */
    parity(cached,original);
    assert(!memcmp(battle,&unchanged,sizeof(unchanged)));
    assert(a.calculations==b.calculations && a.hits==b.hits);
    assert(a.valid==b.valid);
    free(cached);free(original);
}
static void state_and_overlay_parity(void) {
    FojBattle battle;
    foj_battle_init(&battle);
    foj_iso_base_cache_init(&cache);
    check(&battle,true,false);  /* cold raster */
    check(&battle,true,true);   /* warm raster */
    check(&battle,false,true);  /* presentation toggle is not part of base */
    assert(foj_battle_confirm(&battle)==FOJ_BATTLE_SELECTED);
    check(&battle,true,false);  /* selection changes base tile highlights */
    check(&battle,true,true);
    foj_battle_move_cursor(&battle,1,0);
    check(&battle,true,false);  /* cursor AND route change */
    check(&battle,false,true);  /* threat overlay only */
    assert(foj_battle_cancel(&battle)==FOJ_BATTLE_CANCELED);
    check(&battle,true,false);
    assert(foj_battle_guard(&battle)==FOJ_BATTLE_GUARDED);
    check(&battle,true,true);   /* guard HUD changes, scene can be reused */
    battle.hero_hp=2;
    check(&battle,true,true);   /* health overlay changes only */
    battle.enemy_hp=0;
    battle.outcome=FOJ_BATTLE_WON;
    check(&battle,true,false);  /* enemy sprite must disappear */
    check(&battle,true,true);
    assert(cache.hits==7 && cache.misses==5);
    assert(cache.bypasses==0);
}
static void persistent_forecast_is_not_cached_with_pixels(void) {
    FojBattle battle;foj_battle_init(&battle);
    assert(foj_battle_confirm(&battle)==FOJ_BATTLE_SELECTED);
    FojBattleThreatCache cached_threat,normal_threat;
    foj_battle_threat_cache_init(&cached_threat);
    foj_battle_threat_cache_init(&normal_threat);
    foj_iso_base_cache_init(&cache);
    uint32_t *cached=frame(),*normal=frame();
    /* Full threat-cache metrics must evolve exactly as in the uncached
     * renderer, even when the independent terrain cache hits. */
    for(int pass=0;pass<5;++pass) {
        const bool show=pass!=2;
        if(pass==4)foj_battle_move_cursor(&battle,1,0);
        bool was_hit=false;
        foj_iso_render_battle_profiled_base_cached(
            &battle,cached,W,H,STRIDE,show,&cached_threat,
            &cache,&was_hit,NULL,NULL,NULL);
        foj_iso_render_battle_cached_options(
            &battle,normal,W,H,STRIDE,show,&normal_threat);
        parity(cached,normal);
        assert(cached_threat.calculations==normal_threat.calculations);
        assert(cached_threat.hits==normal_threat.hits);
        assert(cached_threat.valid==normal_threat.valid);
        assert(was_hit==(pass>0 && pass<4));
    }
    assert(cached_threat.calculations==1);
    assert(cached_threat.hits==3);
    assert(cache.misses==2 && cache.hits==3);
    free(cached);free(normal);
}

static void all_scene_fields_invalidate(void) {
    FojDemo original,scene;
    foj_demo_init(&original);
    foj_iso_base_cache_init(&cache);
    uint32_t *p=frame(),*gold=frame();
    assert(!foj_iso_base_cache_draw(&cache,&original,p,W,H,STRIDE));
    assert(foj_iso_base_cache_draw(&cache,&original,p,W,H,STRIDE));
    for(int v=0;v<7;++v) {
        scene=original;
        switch(v) {
        case 0: ++scene.hero_x;break;
        case 1: ++scene.hero_y;break;
        case 2: ++scene.enemy_x;break;
        case 3: ++scene.enemy_y;break;
        case 4: ++scene.cursor_x;break;
        case 5: ++scene.cursor_y;break;
        default: scene.selected=!scene.selected;break;
        }
        assert(!foj_iso_base_cache_draw(&cache,&scene,p,W,H,STRIDE));
        foj_iso_render(&scene,gold,W,H,STRIDE);
        parity(p,gold);
        assert(foj_iso_base_cache_draw(&cache,&scene,p,W,H,STRIDE));
        assert(!foj_iso_base_cache_draw(&cache,&original,p,W,H,STRIDE));
    }
    scene=original;
    ++scene.cells[0][0].elevation;
    assert(!foj_iso_base_cache_draw(&cache,&scene,p,W,H,STRIDE));
    foj_iso_render(&scene,gold,W,H,STRIDE);parity(p,gold);
    scene=original;scene.cells[2][3].blocked=!scene.cells[2][3].blocked;
    assert(!foj_iso_base_cache_draw(&cache,&scene,p,W,H,STRIDE));
    foj_iso_render(&scene,gold,W,H,STRIDE);parity(p,gold);
    assert(!foj_iso_base_cache_draw(&cache,&original,p,W,H,STRIDE));
    free(p);free(gold);
}
static void full_resolution_two_buffers_preserve_exact_pixels(void) {
    /* Host-test the real Switch framebuffer size (including a padded
     * row stride and two alternating backbuffers). The small 320x180
     * controls above cannot prove the 1280x720 capacity edge. */
    enum { FW=FOJ_ISO_BASE_CACHE_WIDTH,
           FH=FOJ_ISO_BASE_CACHE_HEIGHT, FS=FW+8 };
    const size_t len=(size_t)FS*(size_t)FH;
    uint32_t *buffers[2]={malloc(len*sizeof(uint32_t)),
                           malloc(len*sizeof(uint32_t))};
    uint32_t *reference=malloc(len*sizeof(uint32_t));
    assert(buffers[0] && buffers[1] && reference);
    FojBattle battle;foj_battle_init(&battle);
    foj_iso_base_cache_init(&cache);
    for (int state=0;state<6;++state) {
        if (state==2)battle.hero_hp=3;
        if (state==3)
            assert(foj_battle_confirm(&battle)==FOJ_BATTLE_SELECTED);
        if (state==4)foj_battle_move_cursor(&battle,1,0);
        const bool show=state!=5;
        const bool expect_hit=state==1 || state==2 || state==5;
        uint32_t *visible=buffers[state%2];
        for (size_t n=0;n<len;++n) {
            visible[n]=UINT32_C(0x12345678);
            reference[n]=UINT32_C(0x12345678);
        }
        FojBattleThreatCache threat_a,threat_b;
        foj_battle_threat_cache_init(&threat_a);
        foj_battle_threat_cache_init(&threat_b);
        bool hit=false;
        foj_iso_render_battle_profiled_base_cached(
            &battle,visible,FW,FH,FS,show,&threat_a,&cache,&hit,
            NULL,NULL,NULL);
        foj_iso_render_battle_cached_options(
            &battle,reference,FW,FH,FS,show,&threat_b);
        assert(hit==expect_hit);
        for (int y=0;y<FH;++y) {
            const size_t start=(size_t)y*(size_t)FS;
            assert(!memcmp(visible+start,reference+start,
                           (size_t)FW*sizeof(uint32_t)));
            for (int x=FW;x<FS;++x) {
                assert(visible[start+(size_t)x]==UINT32_C(0x12345678));
                assert(reference[start+(size_t)x]==UINT32_C(0x12345678));
            }
        }
    }
    assert(cache.hits==3 && cache.misses==3);
    free(reference);free(buffers[0]);free(buffers[1]);
}

static void dimensions_and_invalid_inputs(void) {
    FojDemo scene;foj_demo_init(&scene);
    foj_iso_base_cache_init(&cache);
    uint32_t *p=frame();
    assert(!foj_iso_base_cache_draw(NULL,&scene,p,W,H,STRIDE));
    assert(!foj_iso_base_cache_draw(&cache,&scene,p,W,H,STRIDE));
    assert(foj_iso_base_cache_draw(&cache,&scene,p,W,H,STRIDE));
    assert(!foj_iso_base_cache_draw(&cache,&scene,p,W-1,H,STRIDE));
    assert(cache.misses==2);
    assert(!foj_iso_base_cache_draw(&cache,&scene,p,W,H-1,STRIDE));
    assert(cache.misses==3);
    /* Unsupported dimensions delegate to the original renderer, not a
     * truncated cache. Invalid arguments don't mutate the cache at all. */
    uint32_t *large=calloc(1281u,sizeof(uint32_t));assert(large);
    assert(!foj_iso_base_cache_draw(&cache,&scene,large,1281,1,1281));
    assert(cache.bypasses==1);
    uint32_t *tall=calloc(721u,sizeof(uint32_t));assert(tall);
    assert(!foj_iso_base_cache_draw(&cache,&scene,tall,1,721,1));
    assert(cache.bypasses==2);
    assert(!foj_iso_base_cache_draw(&cache,NULL,p,W,H,STRIDE));
    assert(!foj_iso_base_cache_draw(&cache,&scene,NULL,W,H,STRIDE));
    assert(!foj_iso_base_cache_draw(&cache,&scene,p,W,H,W-1));
    assert(cache.bypasses==2 && cache.misses==3);
    cache.hits=UINT64_MAX;
    assert(!foj_iso_base_cache_draw(&cache,&scene,p,W,H,STRIDE));
    assert(foj_iso_base_cache_draw(&cache,&scene,p,W,H,STRIDE));
    assert(cache.hits==UINT64_MAX);
    free(large);free(tall);free(p);
}
int main(void) {
    state_and_overlay_parity();
    persistent_forecast_is_not_cached_with_pixels();
    all_scene_fields_invalidate();
    full_resolution_two_buffers_preserve_exact_pixels();
    dimensions_and_invalid_inputs();
    return EXIT_SUCCESS;
}
