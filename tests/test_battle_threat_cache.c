/* Stage237: generated-only cache parity; no original PS3 logic/assets. */
#include "battle_replay.h"
#include "isometric_demo.h"

#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static void equal_to_uncached(FojBattleThreatCache *cache,FojBattle *b) {
    FojBattleThreatPreview plain,cached;
    const FojBattle before=*b;
    assert(foj_battle_preview_movement_threat(b,&plain));
    assert(foj_battle_preview_movement_threat_cached(cache,b,&cached));
    assert(memcmp(&plain,&cached,sizeof(plain))==0);
    assert(memcmp(&before,b,sizeof(before))==0);
}

static void test_hover_never_recalculates(void) {
    FojBattle b;
    FojBattleThreatCache cache;
    foj_battle_init(&b);
    assert(foj_battle_confirm(&b)==FOJ_BATTLE_SELECTED);
    foj_battle_threat_cache_init(&cache);
    equal_to_uncached(&cache,&b);
    assert(cache.valid && cache.calculations==1 && cache.hits==0);
    /* Cursor travel must change the marker, not the expensive risk map. */
    for(int y=0;y<FOJ_HEIGHT;++y)
        for(int x=0;x<FOJ_WIDTH;++x) {
            b.map.cursor_x=x;
            b.map.cursor_y=y;
            equal_to_uncached(&cache,&b);
        }
    assert(cache.calculations==1);
    assert(cache.hits==(uint32_t)FOJ_TILE_COUNT);
}

static void test_all_relevant_inputs_invalidate(void) {
    FojBattle b;
    FojBattleThreatCache cache;
    foj_battle_threat_cache_init(&cache);
    foj_battle_init(&b);
    assert(foj_battle_confirm(&b)==FOJ_BATTLE_SELECTED);
    equal_to_uncached(&cache,&b);
    assert(cache.calculations==1);
    b.hero_hp=1;
    equal_to_uncached(&cache,&b);
    assert(cache.calculations==2);
    b.map.cells[2][2].blocked=true;
    equal_to_uncached(&cache,&b);
    assert(cache.calculations==3);
    b.map.cells[3][4].elevation=0;
    equal_to_uncached(&cache,&b);
    assert(cache.calculations==4);
    b.map.enemy_y=4;
    equal_to_uncached(&cache,&b);
    assert(cache.calculations==5);
    ++b.turn_number;
    equal_to_uncached(&cache,&b);
    assert(cache.calculations==6);

    /* ZR can alter incoming damage even when all terrain is unchanged. */
    foj_battle_init(&b);
    assert(foj_battle_guard(&b)==FOJ_BATTLE_GUARDED);
    assert(foj_battle_confirm(&b)==FOJ_BATTLE_SELECTED);
    equal_to_uncached(&cache,&b);
    assert(cache.calculations==7);
    FojBattleThreatPreview guarded;
    assert(foj_battle_preview_movement_threat_cached(&cache,&b,&guarded));
    assert(cache.calculations==7);
    FojBattle unguarded=b;
    unguarded.guarded_this_turn=false;
    unguarded.attacked_this_turn=false;
    FojBattleThreatPreview bare;
    assert(foj_battle_preview_movement_threat(&unguarded,&bare));
    bool changed=false;
    for(int y=0;y<FOJ_HEIGHT;++y)
        for(int x=0;x<FOJ_WIDTH;++x)
            if(bare.incoming_damage[y][x]!=guarded.incoming_damage[y][x])
                changed=true;
    assert(changed);
    equal_to_uncached(&cache,&unguarded);
    assert(cache.calculations==8);
}

static void test_invalid_state_does_not_reuse_stale_matrix(void) {
    FojBattle b;
    FojBattleThreatCache cache;
    FojBattleThreatPreview preview;
    foj_battle_threat_cache_init(&cache);
    foj_battle_init(&b);
    assert(foj_battle_confirm(&b)==FOJ_BATTLE_SELECTED);
    equal_to_uncached(&cache,&b);
    assert(cache.valid);
    assert(!foj_battle_preview_movement_threat_cached(&cache,&b,NULL));
    assert(cache.valid); /* bad output pointer changes no cache */
    assert(foj_battle_cancel(&b)==FOJ_BATTLE_CANCELED);
    memset(&preview,0xab,sizeof(preview));
    assert(!foj_battle_preview_movement_threat_cached(&cache,&b,&preview));
    assert(!cache.valid);
    FojBattleThreatPreview zero={0};
    assert(memcmp(&zero,&preview,sizeof(preview))==0);
    assert(foj_battle_confirm(&b)==FOJ_BATTLE_SELECTED);
    equal_to_uncached(&cache,&b);
    assert(cache.calculations==2);
    b.outcome=FOJ_BATTLE_WON;
    assert(!foj_battle_preview_movement_threat_cached(&cache,&b,&preview));
    assert(!cache.valid);
    assert(memcmp(&zero,&preview,sizeof(preview))==0);
    assert(!foj_battle_preview_movement_threat_cached(&cache,NULL,&preview));
    assert(memcmp(&zero,&preview,sizeof(preview))==0);
}

static void frame_equal(FojBattle *battle,FojBattleThreatCache *cache,
                        uint32_t *plain,uint32_t *optimized,bool shown) {
    enum { WIDTH=1280,HEIGHT=720 };
    const FojBattle before=*battle;
    foj_iso_render_battle_options(battle,plain,WIDTH,HEIGHT,WIDTH,shown);
    foj_iso_render_battle_cached_options(battle,optimized,WIDTH,HEIGHT,WIDTH,
                                         shown,cache);
    assert(memcmp(plain,optimized,(size_t)WIDTH*HEIGHT*sizeof(*plain))==0);
    assert(memcmp(battle,&before,sizeof(*battle))==0);
}

static void test_pixel_parity_after_commands(void) {
    enum { WIDTH=1280,HEIGHT=720 };
    const size_t n=(size_t)WIDTH*HEIGHT;
    uint32_t *plain=calloc(n,sizeof(*plain));
    uint32_t *optimized=calloc(n,sizeof(*optimized));
    assert(plain && optimized);
    FojBattle b;
    FojBattleReplay history;
    FojBattleThreatCache cache;
    FojBattleEvent event;
    foj_battle_init(&b);
    foj_replay_init(&history);
    foj_battle_threat_cache_init(&cache);

    assert(foj_replay_record(&history,&b,FOJ_REPLAY_A,&event));
    assert(event==FOJ_BATTLE_SELECTED);
    frame_equal(&b,&cache,plain,optimized,true);
    assert(cache.calculations==1);
    assert(foj_replay_record(&history,&b,FOJ_REPLAY_RIGHT,&event));
    frame_equal(&b,&cache,plain,optimized,true);
    assert(cache.calculations==1 && cache.hits==1);
    frame_equal(&b,&cache,plain,optimized,false);
    frame_equal(&b,&cache,plain,optimized,true);
    assert(cache.calculations==1 && cache.hits==2);
    assert(foj_replay_record(&history,&b,FOJ_REPLAY_A,&event));
    assert(event==FOJ_BATTLE_MOVED);
    frame_equal(&b,&cache,plain,optimized,true);
    assert(!cache.valid);
    assert(foj_replay_record(&history,&b,FOJ_REPLAY_Y,&event));
    frame_equal(&b,&cache,plain,optimized,true);
    assert(foj_replay_matches(&history,&b));
    assert(foj_replay_record(&history,&b,FOJ_REPLAY_RESET,&event));
    frame_equal(&b,&cache,plain,optimized,true);
    assert(foj_replay_matches(&history,&b));
    free(plain);
    free(optimized);
}

int main(void) {
    test_hover_never_recalculates();
    test_all_relevant_inputs_invalidate();
    test_invalid_state_does_not_reuse_stale_matrix();
    test_pixel_parity_after_commands();
    puts("Stage237 synthetic forecast cache: parity, invalidation, replay and pixels OK");
    return 0;
}
