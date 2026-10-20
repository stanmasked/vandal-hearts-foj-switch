/* Stage248: host controls with a synthetic clock; never claim host FPS. */
#include "base_cache_pair_probe.h"
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
static uint64_t frozen(void *ctx) {(void)ctx;return UINT64_C(42);}
static void test_pairs_and_scene_invalidation(void) {
    FojBasePairProbe *p=calloc(1,sizeof(*p));
    uint32_t *a=calloc(N,sizeof(*a)),*b=calloc(N,sizeof(*b));
    assert(p && a && b);
    foj_base_pair_init(p);
    FojBattle battle;foj_battle_init(&battle);
    assert(foj_battle_confirm(&battle)==FOJ_BATTLE_SELECTED);
    FojBattle preserved=battle;
    Clock clock={0,UINT64_C(1000000)};
    for(int i=0;i<FOJ_BASE_PAIR_WINDOW;++i) {
        assert(foj_base_pair_step(p,&battle,true,a,b,W,H,W,tick,&clock));
        assert(memcmp(a,b,N*sizeof(*a))==0);
    }
    assert(p->ready && p->parity_ok && !p->failed);
    assert(p->cached_mean_us==1000 && p->uncached_mean_us==1000);
    assert(p->completed_windows==1 && p->total_pairs==32);
    assert(p->base_cache.hits==32 && p->base_cache.misses==1);
    assert(memcmp(&battle,&preserved,sizeof(battle))==0);
    /* Struct padding may differ between semantically identical battles.
     * Every named gameplay field is equal, so probes must not reset. */
    FojBattle equivalent;
    memset(&equivalent,0xa5,sizeof(equivalent));
    equivalent.map=battle.map;
    equivalent.hero_hp=battle.hero_hp;
    equivalent.enemy_hp=battle.enemy_hp;
    equivalent.moved_this_turn=battle.moved_this_turn;
    equivalent.previous_hero_x=battle.previous_hero_x;
    equivalent.previous_hero_y=battle.previous_hero_y;
    equivalent.attacked_this_turn=battle.attacked_this_turn;
    equivalent.guarded_this_turn=battle.guarded_this_turn;
    equivalent.turn_number=battle.turn_number;
    equivalent.outcome=battle.outcome;
    assert(foj_base_pair_step(p,&equivalent,true,a,b,W,H,W,tick,&clock));
    assert(p->total_pairs==33 && p->completed_windows==1);
    assert(p->base_cache.hits==33 && p->base_cache.misses==1);
    /* Cursor is a meaningful base-render key: MUST restart measurement. */
    foj_battle_move_cursor(&battle,1,0);
    assert(foj_base_pair_step(p,&battle,true,a,b,W,H,W,tick,&clock));
    assert(!p->ready && p->total_pairs==1 && p->base_cache.misses==1);
    assert(p->base_cache.hits==1);
    battle.map.cells[0][0].elevation++;
    assert(foj_base_pair_step(p,&battle,true,a,b,W,H,W,tick,&clock));
    assert(p->total_pairs==1);
    assert(foj_base_pair_step(p,&battle,false,a,b,W,H,W,tick,&clock));
    assert(p->total_pairs==1 && p->base_cache.hits==1);
    free(a);free(b);free(p);
}
static void test_fail_closed_and_draw(void) {
    FojBasePairProbe *p=calloc(1,sizeof(*p));
    uint32_t *a=calloc(N,sizeof(*a)),*b=calloc(N,sizeof(*b));
    assert(p && a && b);
    FojBattle battle;foj_battle_init(&battle);
    foj_base_pair_init(p);
    assert(!foj_base_pair_step(p,&battle,true,a,b,W,H,W,frozen,NULL));
    assert(p->failed && !p->parity_ok && !p->ready);
    Clock clk={0,UINT64_C(1000000)};
    assert(!foj_base_pair_step(p,&battle,true,a,b,W,H,W,tick,&clk));
    foj_base_pair_init(p);
    assert(!foj_base_pair_step(p,&battle,true,a,a,W,H,W,tick,&clk));
    assert(!foj_base_pair_step(p,&battle,true,a,b,W,H,W+1,tick,&clk));
    assert(!foj_base_pair_step(p,&battle,true,a,b,W,0,W,tick,&clk));
    assert(!foj_base_pair_step(NULL,&battle,true,a,b,W,H,W,tick,&clk));
    assert(!foj_base_pair_step(p,&battle,true,a,b,W,H,W,NULL,NULL));
    assert(!foj_base_pair_step(p,&battle,true,a,b,
                               FOJ_ISO_BASE_CACHE_WIDTH+1,H,
                               FOJ_ISO_BASE_CACHE_WIDTH+1,tick,&clk));
    /* Saturated barcode is invalid, not clamped or silently accepted. */
    foj_base_pair_init(p);
    clk.step=UINT64_C(70000000);
    for(int i=0;i<FOJ_BASE_PAIR_WINDOW-1;++i)
        assert(foj_base_pair_step(p,&battle,false,a,b,W,H,W,tick,&clk));
    assert(!foj_base_pair_step(p,&battle,false,a,b,W,H,W,tick,&clk));
    assert(p->failed);
    const int dw=932,dh=20;
    uint32_t *screen=calloc((size_t)dw*dh,sizeof(*screen));
    assert(screen);
    assert(foj_base_pair_draw(p,screen,dw,dh,dw));
    assert(screen[FOJ_BASE_PAIR_Y*dw+FOJ_BASE_PAIR_STATUS_X]==
           UINT32_C(0xff3030ff));
    assert(!foj_base_pair_draw(p,screen,dw-1,dh,dw));
    assert(!foj_base_pair_draw(p,screen,dw,dh-1,dw));
    assert(!foj_base_pair_draw(p,screen,dw,dh,dw-1));
    assert(!foj_base_pair_draw(p,NULL,dw,dh,dw));
    free(screen);free(a);free(b);free(p);
}
int main(void) {
    test_pairs_and_scene_invalidation();
    test_fail_closed_and_draw();
    return EXIT_SUCCESS;
}
