/* Stage236: source-only exhaustive input-to-preview parity for invented battle.
 * No original PS3 data, AI, geometry, assets, or engine assumptions. */
#include "battle_replay.h"

#include <assert.h>
#include <stdio.h>
#include <string.h>

static FojBattleEvent press(FojBattleReplay *history,FojBattle *battle,
                            FojReplayCommand command) {
    FojBattleEvent event=FOJ_BATTLE_REJECTED;
    assert(foj_replay_record(history,battle,command,&event));
    assert(foj_replay_matches(history,battle));
    return event;
}

static void drive_to(FojBattleReplay *history,FojBattle *battle,
                     int target_x,int target_y) {
    while(battle->map.cursor_x<target_x)
        (void)press(history,battle,FOJ_REPLAY_RIGHT);
    while(battle->map.cursor_x>target_x)
        (void)press(history,battle,FOJ_REPLAY_LEFT);
    while(battle->map.cursor_y<target_y)
        (void)press(history,battle,FOJ_REPLAY_DOWN);
    while(battle->map.cursor_y>target_y)
        (void)press(history,battle,FOJ_REPLAY_UP);
    assert(battle->map.cursor_x==target_x && battle->map.cursor_y==target_y);
}

static void exhaustive_live_replay_parity(bool guard) {
    FojBattle selected;
    foj_battle_init(&selected);
    if (guard) assert(foj_battle_guard(&selected)==FOJ_BATTLE_GUARDED);
    assert(foj_battle_confirm(&selected)==FOJ_BATTLE_SELECTED);
    const FojBattle before=selected;
    FojBattleThreatPreview preview;
    assert(foj_battle_preview_movement_threat(&selected,&preview));
    assert(memcmp(&before,&selected,sizeof(before))==0);

    int legal=0, safe=0, dangerous=0;
    for(int y=0;y<FOJ_HEIGHT;++y)
        for(int x=0;x<FOJ_WIDTH;++x) {
            if(!preview.can_move[y][x])continue;
            ++legal;

            FojBattle live;
            FojBattleReplay history;
            foj_battle_init(&live);
            foj_replay_init(&history);
            if(guard) assert(press(&history,&live,FOJ_REPLAY_ZR)==FOJ_BATTLE_GUARDED);
            assert(press(&history,&live,FOJ_REPLAY_A)==FOJ_BATTLE_SELECTED);
            drive_to(&history,&live,x,y);
            assert(press(&history,&live,FOJ_REPLAY_A)==FOJ_BATTLE_MOVED);
            assert(live.map.hero_x==x && live.map.hero_y==y);
            const uint8_t hp_before=live.hero_hp;
            FojEnemyTurnForecast forecast;
            assert(foj_battle_forecast_enemy_turn(&live,&forecast));
            const FojBattle before_y=live;
            const FojBattleEvent event=press(&history,&live,FOJ_REPLAY_Y);
            assert(memcmp(&before_y,&live,sizeof(before_y))!=0);
            assert(event==forecast.event);
            assert(live.hero_hp==forecast.hero_hp_after);
            assert(live.map.enemy_x==forecast.enemy_x_after);
            assert(live.map.enemy_y==forecast.enemy_y_after);
            assert(live.turn_number==forecast.turn_after);
            assert(live.outcome==forecast.outcome_after);
            assert((unsigned)(hp_before-live.hero_hp)==
                   (unsigned)preview.incoming_damage[y][x]);
            assert((int)preview.enemy_x_after[y][x]==live.map.enemy_x);
            assert((int)preview.enemy_y_after[y][x]==live.map.enemy_y);
            assert(foj_replay_matches(&history,&live));
            if(live.hero_hp==hp_before)++safe;else ++dangerous;
        }
    assert(legal>=5 && safe>0 && dangerous>0);
    assert(memcmp(&before,&selected,sizeof(before))==0);
    printf("Stage236 guard=%d: %d destinations, %d safe, %d dangerous\n",
           guard?1:0,legal,safe,dangerous);
}

static void low_hp_defeat_parity(bool guard) {
    FojBattle selected;
    foj_battle_init(&selected);
    selected.hero_hp=1;
    if(guard) assert(foj_battle_guard(&selected)==FOJ_BATTLE_GUARDED);
    assert(foj_battle_confirm(&selected)==FOJ_BATTLE_SELECTED);
    const FojBattle before=selected;
    FojBattleThreatPreview preview;
    assert(foj_battle_preview_movement_threat(&selected,&preview));
    int checked=0, defeated=0;
    for(int y=0;y<FOJ_HEIGHT;++y)
        for(int x=0;x<FOJ_WIDTH;++x){
            if(!preview.can_move[y][x])continue;
            FojBattle committed=selected;
            while(committed.map.cursor_x<x)foj_battle_move_cursor(&committed,1,0);
            while(committed.map.cursor_x>x)foj_battle_move_cursor(&committed,-1,0);
            while(committed.map.cursor_y<y)foj_battle_move_cursor(&committed,0,1);
            while(committed.map.cursor_y>y)foj_battle_move_cursor(&committed,0,-1);
            assert(foj_battle_confirm(&committed)==FOJ_BATTLE_MOVED);
            FojEnemyTurnForecast forecast;
            assert(foj_battle_forecast_enemy_turn(&committed,&forecast));
            const FojBattleEvent event=foj_battle_end_turn(&committed);
            assert(event==forecast.event);
            assert(committed.hero_hp==forecast.hero_hp_after);
            assert(committed.outcome==forecast.outcome_after);
            assert(committed.map.enemy_x==preview.enemy_x_after[y][x]);
            assert(committed.map.enemy_y==preview.enemy_y_after[y][x]);
            assert(preview.incoming_damage[y][x]==1-committed.hero_hp);
            if(committed.outcome==FOJ_BATTLE_LOST)++defeated;
            ++checked;
        }
    assert(checked>=5 && defeated>0);
    assert(memcmp(&before,&selected,sizeof(before))==0);
}

static void rejected_targets_have_no_preview_or_committed_move(void) {
    FojBattle selected;
    foj_battle_init(&selected);
    assert(foj_battle_confirm(&selected)==FOJ_BATTLE_SELECTED);
    FojBattleThreatPreview preview;
    assert(foj_battle_preview_movement_threat(&selected,&preview));
    const int blocked[][2]={{2,1},{2,3},{6,3},{1,2}};
    for(unsigned i=0;i<sizeof(blocked)/sizeof(blocked[0]);++i){
        int x=blocked[i][0],y=blocked[i][1];
        assert(!preview.can_move[y][x]);
        assert(preview.incoming_damage[y][x]==0);
        FojBattle live=selected;
        while(live.map.cursor_x<x)foj_battle_move_cursor(&live,1,0);
        while(live.map.cursor_x>x)foj_battle_move_cursor(&live,-1,0);
        while(live.map.cursor_y<y)foj_battle_move_cursor(&live,0,1);
        while(live.map.cursor_y>y)foj_battle_move_cursor(&live,0,-1);
        assert(foj_battle_confirm(&live)!=FOJ_BATTLE_MOVED);
        assert(live.map.hero_x==selected.map.hero_x);
        assert(live.map.hero_y==selected.map.hero_y);
    }
}

int main(void){
    exhaustive_live_replay_parity(false);
    exhaustive_live_replay_parity(true);
    low_hp_defeat_parity(false);
    low_hp_defeat_parity(true);
    rejected_targets_have_no_preview_or_committed_move();
    puts("Stage236 synthetic threat vs actual controller replay: five scenarios passed");
    return 0;
}
