/* Native fail-closed controls for Stage245 whole CPU-rasterizer pairs.
 * The clock is synthetic: no claim about host GPU, FPS or real Switch. */
#include "render_pair_probe.h"
#include <assert.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>

enum { W=320, H=180, N=W*H };
typedef struct { uint64_t stamp, step; } Clock;
static uint64_t tick(void *ctx) {
    Clock *c=(Clock *)ctx;
    c->stamp+=c->step;
    return c->stamp;
}
static uint64_t frozen(void *ctx) {
    (void)ctx;
    return UINT64_C(42);
}
static uint32_t *pixels(void) {
    uint32_t *result=(uint32_t *)calloc(N,sizeof(uint32_t));
    assert(result);
    return result;
}
static void step(FojRenderPairProbe *meter,FojBattle *battle,bool show,
                 uint32_t *a,uint32_t *b,Clock *clock) {
    assert(foj_render_pair_step(meter,battle,show,a,b,W,H,W,tick,clock));
    assert(!memcmp(a,b,N*sizeof(uint32_t)));
}
static void test_selected_pair_parity_and_cache(void) {
    FojBattle battle, original;
    foj_battle_init(&battle);
    assert(foj_battle_confirm(&battle)==FOJ_BATTLE_SELECTED);
    original=battle;
    FojRenderPairProbe meter;
    foj_render_pair_init(&meter);
    uint32_t *a=pixels(),*b=pixels();
    Clock clock={0,UINT64_C(4000000)};
    for(int i=0;i<FOJ_RENDER_PAIR_WINDOW;i++) {
        step(&meter,&battle,true,a,b,&clock);
        assert(meter.total_pairs==(unsigned)i+1);
    }
    assert(meter.ready && meter.parity_ok && !meter.failed);
    assert(meter.cached_mean_us==4000 && meter.uncached_mean_us==4000);
    assert(meter.completed_windows==1);
    assert(meter.cache.calculations==1u);
    assert(meter.cache.hits>0u);
    assert(!memcmp(&battle,&original,sizeof(battle)));
    /* Cursor changes are safe hits for the existing forecast key. */
    foj_battle_move_cursor(&battle,1,0);
    step(&meter,&battle,true,a,b,&clock);
    assert(meter.total_pairs==FOJ_RENDER_PAIR_WINDOW+1u);
    assert(meter.cache.calculations==1u);
    /* Meaningful map changes must invalidate and restart the window. */
    battle.map.cells[0][0].blocked=!battle.map.cells[0][0].blocked;
    step(&meter,&battle,true,a,b,&clock);
    assert(meter.total_pairs==1u && !meter.ready);
    assert(meter.cache.calculations==1u);
    free(a);free(b);
}
static void test_no_forecast_control_state(void) {
    FojBattle battle;
    foj_battle_init(&battle);
    FojRenderPairProbe meter;
    foj_render_pair_init(&meter);
    Clock clock={0,UINT64_C(4000000)};
    uint32_t *a=pixels(),*b=pixels();
    for(int i=0;i<FOJ_RENDER_PAIR_WINDOW;i++)
        step(&meter,&battle,true,a,b,&clock);
    assert(meter.ready && meter.cache.hits==0u);
    assert(meter.cached_mean_us==4000);
    /* Changing only overlay enable is a *new* scene. */
    step(&meter,&battle,false,a,b,&clock);
    assert(meter.total_pairs==1u && !meter.ready);
    assert(meter.cache.hits==0u);
    free(a);free(b);
}
static void test_clock_and_bounds_fail_closed(void) {
    FojBattle battle;foj_battle_init(&battle);
    FojRenderPairProbe meter;foj_render_pair_init(&meter);
    uint32_t *a=pixels(),*b=pixels();
    assert(!foj_render_pair_step(&meter,&battle,true,a,b,W,H,W,frozen,NULL));
    assert(meter.failed && !meter.parity_ok && !meter.ready);
    Clock clock={0,UINT64_C(4000000)};
    assert(!foj_render_pair_step(&meter,&battle,true,a,b,W,H,W,tick,&clock));
    foj_render_pair_init(&meter);
    assert(!foj_render_pair_step(&meter,&battle,true,a,a,W,H,W,tick,&clock));
    assert(!foj_render_pair_step(&meter,&battle,true,a,b,W,H,W+1,tick,&clock));
    assert(!foj_render_pair_step(&meter,&battle,true,a,b,W,0,W,tick,&clock));
    assert(!foj_render_pair_step(NULL,&battle,true,a,b,W,H,W,tick,&clock));
    assert(!foj_render_pair_step(&meter,&battle,true,a,b,W,H,W,NULL,NULL));
    free(a);free(b);
}
static void test_overflow_and_draw(void) {
    FojBattle battle;foj_battle_init(&battle);
    FojRenderPairProbe meter;foj_render_pair_init(&meter);
    uint32_t *a=pixels(),*b=pixels();
    Clock clock={0,UINT64_C(65535000)};
    for(int i=0;i<FOJ_RENDER_PAIR_WINDOW-1;i++)
        step(&meter,&battle,true,a,b,&clock);
    assert(!foj_render_pair_step(&meter,&battle,true,a,b,W,H,W,tick,&clock));
    assert(meter.failed && !meter.ready);
    const int dw=932,dh=20;
    uint32_t *screen=(uint32_t *)calloc((size_t)dw*dh,sizeof(uint32_t));
    assert(screen);
    assert(foj_render_pair_draw(&meter,screen,dw,dh,dw));
    assert(screen[FOJ_RENDER_PAIR_Y*dw+FOJ_RENDER_PAIR_STATUS_X] ==
           UINT32_C(0xff2222ff));
    assert(!foj_render_pair_draw(&meter,screen,931,dh,932));
    assert(!foj_render_pair_draw(&meter,screen,dw,19,dw));
    assert(!foj_render_pair_draw(&meter,screen,dw,dh,931));
    assert(!foj_render_pair_draw(&meter,NULL,dw,dh,dw));
    assert(!foj_render_pair_draw(NULL,screen,dw,dh,dw));
    free(screen);free(a);free(b);
}
int main(void) {
    test_selected_pair_parity_and_cache();
    test_no_forecast_control_state();
    test_clock_and_bounds_fail_closed();
    test_overflow_and_draw();
    return EXIT_SUCCESS;
}
