/* Generated-only Stage228 battle history, bounded and deterministic. */
#include "battle_replay.h"

#include <assert.h>
#include <stdio.h>
#include <string.h>

static FojBattleEvent send(FojBattleReplay *log, FojBattle *battle,
                           FojReplayCommand command) {
    FojBattleEvent event = FOJ_BATTLE_REJECTED;
    assert(foj_replay_record(log, battle, command, &event));
    assert(foj_replay_matches(log, battle));
    return event;
}

static void test_complete_guest_style_victory(void) {
    FojBattleReplay log;
    FojBattle live, copy;
    foj_replay_init(&log);
    foj_battle_init(&live);
    assert(foj_replay_matches(&log, &live));
    assert(send(&log, &live, FOJ_REPLAY_A) == FOJ_BATTLE_SELECTED);
    for(int i=0;i<4;++i)send(&log,&live,FOJ_REPLAY_RIGHT);
    assert(send(&log,&live,FOJ_REPLAY_A)==FOJ_BATTLE_MOVED);
    assert(send(&log,&live,FOJ_REPLAY_Y)==FOJ_BATTLE_ENEMY_ATTACKED);
    send(&log,&live,FOJ_REPLAY_RIGHT);
    assert(send(&log,&live,FOJ_REPLAY_X)==FOJ_BATTLE_ATTACKED);
    assert(send(&log,&live,FOJ_REPLAY_Y)==FOJ_BATTLE_ENEMY_ATTACKED);
    assert(send(&log,&live,FOJ_REPLAY_X)==FOJ_BATTLE_VICTORY);
    assert(live.outcome==FOJ_BATTLE_WON);
    assert(live.hero_hp==4 && live.enemy_hp==0);
    assert(send(&log,&live,FOJ_REPLAY_Y)==FOJ_BATTLE_REJECTED);
    assert(foj_replay_reconstruct(&log,&copy));
    assert(memcmp(&copy,&live,sizeof(live))==0);
    assert(log.count==12);
}

static void test_b_undo_new_route_then_guard(void) {
    FojBattleReplay log;
    FojBattle b;
    foj_replay_init(&log); foj_battle_init(&b);
    assert(send(&log,&b,FOJ_REPLAY_A)==FOJ_BATTLE_SELECTED);
    send(&log,&b,FOJ_REPLAY_RIGHT);
    send(&log,&b,FOJ_REPLAY_RIGHT);
    assert(send(&log,&b,FOJ_REPLAY_A)==FOJ_BATTLE_MOVED);
    assert(send(&log,&b,FOJ_REPLAY_B)==FOJ_BATTLE_MOVE_UNDONE);
    assert(b.map.hero_x==1 && b.map.hero_y==2);
    assert(send(&log,&b,FOJ_REPLAY_A)==FOJ_BATTLE_SELECTED);
    send(&log,&b,FOJ_REPLAY_RIGHT);
    assert(send(&log,&b,FOJ_REPLAY_A)==FOJ_BATTLE_MOVED);
    assert(b.map.hero_x==2);
    assert(send(&log,&b,FOJ_REPLAY_ZR)==FOJ_BATTLE_GUARDED);
    assert(send(&log,&b,FOJ_REPLAY_X)==FOJ_BATTLE_REJECTED);
    assert(send(&log,&b,FOJ_REPLAY_Y)==FOJ_BATTLE_ENEMY_MOVED);
    assert(!b.guarded_this_turn);
    assert(foj_replay_matches(&log,&b));
}

static void test_reset_replay_is_recorded_and_deterministic(void) {
    FojBattleReplay log;
    FojBattle b, reborn;
    foj_replay_init(&log); foj_battle_init(&b);
    assert(send(&log,&b,FOJ_REPLAY_Y)==FOJ_BATTLE_ENEMY_MOVED);
    assert(b.turn_number==2);
    assert(send(&log,&b,FOJ_REPLAY_RESET)==FOJ_BATTLE_NO_ACTION);
    assert(b.turn_number==1 && b.map.hero_x==1 && b.map.enemy_x==6);
    assert(send(&log,&b,FOJ_REPLAY_B)==FOJ_BATTLE_NO_ACTION);
    assert(foj_replay_reconstruct(&log,&reborn));
    assert(memcmp(&reborn,&b,sizeof(b))==0);
}

static void test_tampered_log_or_state_fails_closed(void) {
    FojBattleReplay log;
    FojBattle b, target;
    foj_replay_init(&log); foj_battle_init(&b);
    send(&log,&b,FOJ_REPLAY_RIGHT);
    const FojBattle intact=b;
    b.hero_hp=1;
    assert(!foj_replay_matches(&log,&b));
    b=intact;
    log.commands[0]=255;
    memset(&target,0xa5,sizeof(target));
    FojBattle untouched=target;
    assert(!foj_replay_reconstruct(&log,&target));
    assert(memcmp(&target,&untouched,sizeof(target))==0);
    assert(!foj_replay_matches(&log,&b));
    log.commands[0]=FOJ_REPLAY_RIGHT;
    assert(foj_replay_matches(&log,&b));
    log.count=FOJ_REPLAY_MAX_INPUTS+1;
    assert(!foj_replay_reconstruct(&log,&target));
    assert(!foj_replay_matches(&log,&b));
}

static void test_invalid_commands_are_transactional(void) {
    FojBattleReplay log;
    FojBattle b;
    foj_replay_init(&log); foj_battle_init(&b);
    const FojBattle initial=b;
    FojBattleEvent event=FOJ_BATTLE_NO_ACTION;
    assert(!foj_replay_record(NULL,&b,FOJ_REPLAY_A,&event));
    assert(event==FOJ_BATTLE_REJECTED);
    assert(!foj_replay_record(&log,NULL,FOJ_REPLAY_A,&event));
    assert(!foj_replay_record(&log,&b,(FojReplayCommand)-1,&event));
    assert(!foj_replay_record(&log,&b,FOJ_REPLAY_COMMAND_COUNT,&event));
    assert(log.count==0 && memcmp(&initial,&b,sizeof(b))==0);
    assert(!foj_replay_reconstruct(NULL,&b));
    assert(!foj_replay_reconstruct(&log,NULL));
    assert(!foj_replay_matches(NULL,&b));
    assert(!foj_replay_matches(&log,NULL));
}

static void test_full_log_rejects_without_changing_live_battle(void) {
    FojBattleReplay log;
    FojBattle b;
    foj_replay_init(&log); foj_battle_init(&b);
    for(unsigned i=0;i<FOJ_REPLAY_MAX_INPUTS;++i)
        assert(send(&log,&b,FOJ_REPLAY_LEFT)==FOJ_BATTLE_NO_ACTION);
    FojBattle untouched=b;
    FojBattleReplay intact=log;
    FojBattleEvent event=FOJ_BATTLE_NO_ACTION;
    assert(!foj_replay_record(&log,&b,FOJ_REPLAY_RESET,&event));
    assert(event==FOJ_BATTLE_REJECTED);
    assert(memcmp(&untouched,&b,sizeof(b))==0);
    assert(memcmp(&intact,&log,sizeof(log))==0);
    assert(foj_replay_matches(&log,&b));
}

int main(void) {
    test_complete_guest_style_victory();
    test_b_undo_new_route_then_guard();
    test_reset_replay_is_recorded_and_deterministic();
    test_tampered_log_or_state_fails_closed();
    test_invalid_commands_are_transactional();
    test_full_log_rejects_without_changing_live_battle();
    puts("Stage228 synthetic input replay: six scenarios passed");
    return 0;
}
