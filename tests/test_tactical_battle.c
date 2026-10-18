/* Stage217: no PS3 data or proprietary gameplay rules; generated-only C tests. */
#include "tactical_battle.h"

#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

static void test_init_and_confirm_move_budget(void) {
    FojBattle b;
    foj_battle_init(&b);
    assert(b.hero_hp == FOJ_BATTLE_HERO_MAX_HP);
    assert(b.enemy_hp == FOJ_BATTLE_ENEMY_MAX_HP);
    assert(b.turn_number == 1 && b.outcome == FOJ_BATTLE_ONGOING);
    assert(foj_battle_confirm(&b) == FOJ_BATTLE_SELECTED);
    foj_battle_move_cursor(&b,1,0);
    assert(foj_battle_confirm(&b) == FOJ_BATTLE_MOVED);
    assert(b.map.hero_x == 2 && b.map.hero_y == 2);
    assert(b.moved_this_turn && !b.map.selected);
    assert(foj_battle_confirm(&b) == FOJ_BATTLE_REJECTED);
    assert(!b.map.selected);
    assert(foj_battle_end_turn(&b) == FOJ_BATTLE_ENEMY_MOVED);
    assert(b.turn_number == 2 && !b.moved_this_turn);
    b.map.cursor_x=b.map.hero_x;
    b.map.cursor_y=b.map.hero_y;
    assert(foj_battle_confirm(&b) == FOJ_BATTLE_SELECTED);
    assert(foj_battle_cancel(&b) == FOJ_BATTLE_CANCELED);
    assert(!b.map.selected);
}

static void test_adjacent_attack_and_victory(void) {
    FojBattle b;
    foj_battle_init(&b);
    b.map.hero_x=5; b.map.hero_y=2;
    b.map.enemy_x=6; b.map.enemy_y=2;
    b.map.cursor_x=6; b.map.cursor_y=2;
    assert(foj_battle_attack(&b) == FOJ_BATTLE_ATTACKED);
    assert(b.enemy_hp == 3 && b.attacked_this_turn);
    assert(foj_battle_attack(&b) == FOJ_BATTLE_REJECTED);
    assert(b.enemy_hp == 3);
    assert(foj_battle_end_turn(&b) == FOJ_BATTLE_ENEMY_ATTACKED);
    assert(b.hero_hp == 6 && !b.attacked_this_turn);
    assert(foj_battle_attack(&b) == FOJ_BATTLE_VICTORY);
    assert(b.enemy_hp == 0 && b.outcome == FOJ_BATTLE_WON);
    assert(foj_battle_attack(&b) == FOJ_BATTLE_REJECTED);
    assert(foj_battle_end_turn(&b) == FOJ_BATTLE_REJECTED);
    assert(b.hero_hp == 6);
}

static void test_invalid_targets_and_height_range(void) {
    FojBattle b;
    foj_battle_init(&b);
    b.map.cursor_x=b.map.enemy_x;
    b.map.cursor_y=b.map.enemy_y;
    assert(foj_battle_attack(&b) == FOJ_BATTLE_REJECTED);
    assert(b.enemy_hp == FOJ_BATTLE_ENEMY_MAX_HP);
    b.map.hero_x=5; b.map.hero_y=2;
    b.map.enemy_x=6; b.map.enemy_y=2;
    b.map.cursor_x=5; b.map.cursor_y=2;
    assert(foj_battle_attack(&b) == FOJ_BATTLE_REJECTED);
    b.map.cursor_x=6; b.map.cursor_y=2;
    b.map.cells[2][6].elevation=3; /* impossible +2 step */
    assert(foj_battle_attack(&b) == FOJ_BATTLE_REJECTED);
    assert(b.enemy_hp == FOJ_BATTLE_ENEMY_MAX_HP);
    b.map.cells[2][6].elevation=1;
    b.map.selected=true;
    assert(foj_battle_attack(&b) == FOJ_BATTLE_REJECTED);
    b.map.selected=false;
    assert(foj_battle_attack(&b) == FOJ_BATTLE_ATTACKED);
}

static void test_enemy_moves_and_attacks_deterministically(void) {
    FojBattle a,b;
    foj_battle_init(&a);
    foj_battle_init(&b);
    for (int turn=0;turn<4;++turn) {
        FojBattleEvent ea=foj_battle_end_turn(&a);
        FojBattleEvent eb=foj_battle_end_turn(&b);
        assert(ea==eb);
        assert(a.map.enemy_x==b.map.enemy_x);
        assert(a.map.enemy_y==b.map.enemy_y);
        assert(a.hero_hp==b.hero_hp);
        assert(a.turn_number==b.turn_number);
        assert(foj_in_bounds(a.map.enemy_x,a.map.enemy_y));
        assert(!a.map.cells[a.map.enemy_y][a.map.enemy_x].blocked);
        assert(!(a.map.hero_x==a.map.enemy_x &&
                 a.map.hero_y==a.map.enemy_y));
    }
    assert(a.map.enemy_x != 6 || a.map.enemy_y != 3);
}

static void test_defeat_and_reset(void) {
    FojBattle b;
    foj_battle_init(&b);
    b.hero_hp=FOJ_BATTLE_ENEMY_DAMAGE;
    b.map.hero_x=5; b.map.hero_y=2;
    b.map.enemy_x=6; b.map.enemy_y=2;
    assert(foj_battle_end_turn(&b)==FOJ_BATTLE_DEFEAT);
    assert(b.hero_hp==0 && b.outcome==FOJ_BATTLE_LOST);
    assert(foj_battle_confirm(&b)==FOJ_BATTLE_REJECTED);
    assert(foj_battle_end_turn(&b)==FOJ_BATTLE_REJECTED);
    foj_battle_move_cursor(&b,2,0);
    assert(b.map.cursor_x==1);
    foj_battle_init(&b);
    assert(b.hero_hp==FOJ_BATTLE_HERO_MAX_HP);
    assert(b.outcome==FOJ_BATTLE_ONGOING && b.turn_number==1);
}

static void test_impassable_enemy_and_turn_saturation(void) {
    FojBattle b;
    foj_battle_init(&b);
    const int ex=b.map.enemy_x,ey=b.map.enemy_y;
    for(int y=0;y<FOJ_HEIGHT;++y)
        for(int x=0;x<FOJ_WIDTH;++x)
            if (!(x==b.map.hero_x && y==b.map.hero_y) &&
                !(x==ex && y==ey)) b.map.cells[y][x].blocked=true;
    b.turn_number=UINT16_MAX;
    assert(foj_battle_end_turn(&b)==FOJ_BATTLE_TURN_ENDED);
    assert(b.turn_number==UINT16_MAX);
    assert(b.map.enemy_x==ex && b.map.enemy_y==ey);
    assert(b.hero_hp==FOJ_BATTLE_HERO_MAX_HP);
}

static void test_full_controller_style_playthrough_to_victory(void) {
    FojBattle b;
    foj_battle_init(&b);
    assert(foj_battle_confirm(&b)==FOJ_BATTLE_SELECTED);
    for (int x=0;x<4;++x) foj_battle_move_cursor(&b,1,0);
    assert(b.map.cursor_x==5 && b.map.cursor_y==2);
    assert(foj_battle_confirm(&b)==FOJ_BATTLE_MOVED);
    assert(b.map.hero_x==5 && b.map.hero_y==2);
    assert(foj_battle_end_turn(&b)==FOJ_BATTLE_ENEMY_ATTACKED);
    assert(b.map.enemy_x==6 && b.map.enemy_y==2);
    assert(b.hero_hp==6);
    foj_battle_move_cursor(&b,1,0);
    assert(foj_battle_attack(&b)==FOJ_BATTLE_ATTACKED);
    assert(b.enemy_hp==3);
    assert(foj_battle_end_turn(&b)==FOJ_BATTLE_ENEMY_ATTACKED);
    assert(b.hero_hp==4);
    assert(foj_battle_attack(&b)==FOJ_BATTLE_VICTORY);
    assert(b.outcome==FOJ_BATTLE_WON);
    assert(foj_battle_end_turn(&b)==FOJ_BATTLE_REJECTED);
}

static void test_forecast_is_pure_and_matches_actual_turns(void) {
    FojBattle b;
    foj_battle_init(&b);
    for (int i=0;i<4;++i) {
        FojBattle before=b;
        FojEnemyTurnForecast view;
        assert(foj_battle_forecast_enemy_turn(&b,&view));
        assert(memcmp(&before,&b,sizeof(b))==0);
        FojBattleEvent played=foj_battle_end_turn(&b);
        assert(view.event==played);
        assert(view.enemy_x_after==b.map.enemy_x);
        assert(view.enemy_y_after==b.map.enemy_y);
        assert(view.hero_hp_after==b.hero_hp);
        assert(view.turn_after==b.turn_number);
        assert(view.outcome_after==b.outcome);
    }
}

static void test_forecast_defeat_no_mutation_and_nulls(void) {
    FojBattle b;
    foj_battle_init(&b);
    b.hero_hp=2;
    b.map.hero_x=5; b.map.hero_y=2;
    b.map.enemy_x=6; b.map.enemy_y=2;
    b.map.selected=true;
    b.moved_this_turn=true;
    FojBattle before=b;
    FojEnemyTurnForecast view;
    assert(foj_battle_forecast_enemy_turn(&b,&view));
    assert(memcmp(&before,&b,sizeof(b))==0);
    assert(view.event==FOJ_BATTLE_DEFEAT);
    assert(view.hero_hp_after==0);
    assert(view.outcome_after==FOJ_BATTLE_LOST);
    assert(view.turn_after==2);
    assert(b.hero_hp==2 && b.map.selected);
    assert(foj_battle_end_turn(&b)==view.event);
    memset(&view,0x55,sizeof(view));
    assert(!foj_battle_forecast_enemy_turn(&b,&view));
    assert(view.hero_hp_after==0 && view.turn_after==0);
    assert(!foj_battle_forecast_enemy_turn(NULL,&view));
    assert(!foj_battle_forecast_enemy_turn(&before,NULL));
}

static void test_forecast_immobile_enemy_and_saturated_clock(void) {
    FojBattle b;
    foj_battle_init(&b);
    for(int y=0;y<FOJ_HEIGHT;++y)
        for(int x=0;x<FOJ_WIDTH;++x)
            if ((x!=b.map.hero_x || y!=b.map.hero_y) &&
                (x!=b.map.enemy_x || y!=b.map.enemy_y))
                b.map.cells[y][x].blocked=true;
    b.turn_number=UINT16_MAX;
    FojEnemyTurnForecast view;
    assert(foj_battle_forecast_enemy_turn(&b,&view));
    assert(view.event==FOJ_BATTLE_TURN_ENDED);
    assert(view.turn_after==UINT16_MAX);
    assert(view.enemy_x_after==b.map.enemy_x);
    assert(view.enemy_y_after==b.map.enemy_y);
    assert(view.hero_hp_after==b.hero_hp);
}

static void test_forecast_refreshes_after_hero_reposition(void) {
    FojBattle battle;
    foj_battle_init(&battle);
    FojEnemyTurnForecast initial;
    assert(foj_battle_forecast_enemy_turn(&battle,&initial));
    assert(initial.event==FOJ_BATTLE_ENEMY_MOVED);
    assert(foj_battle_confirm(&battle)==FOJ_BATTLE_SELECTED);
    for (int i=0;i<4;++i) foj_battle_move_cursor(&battle,1,0);
    assert(foj_battle_confirm(&battle)==FOJ_BATTLE_MOVED);
    FojEnemyTurnForecast updated;
    const FojBattle untouched=battle;
    assert(foj_battle_forecast_enemy_turn(&battle,&updated));
    assert(memcmp(&untouched,&battle,sizeof(battle))==0);
    assert(updated.event==FOJ_BATTLE_ENEMY_ATTACKED);
    assert(updated.hero_hp_after==FOJ_BATTLE_HERO_MAX_HP-
                                  FOJ_BATTLE_ENEMY_DAMAGE);
    assert(updated.enemy_x_after==6 && updated.enemy_y_after==2);
    assert(foj_battle_end_turn(&battle)==updated.event);
    assert(battle.hero_hp==updated.hero_hp_after);
}

static void test_guard_halves_damage_and_expires(void) {
    FojBattle b;
    foj_battle_init(&b);
    b.map.hero_x=5; b.map.hero_y=2;
    b.map.enemy_x=6; b.map.enemy_y=2;
    assert(foj_battle_guard(&b)==FOJ_BATTLE_GUARDED);
    assert(b.guarded_this_turn && b.attacked_this_turn);
    FojEnemyTurnForecast prediction;
    const FojBattle unchanged=b;
    assert(foj_battle_forecast_enemy_turn(&b,&prediction));
    assert(memcmp(&unchanged,&b,sizeof(b))==0);
    assert(prediction.event==FOJ_BATTLE_ENEMY_ATTACKED);
    assert(prediction.hero_hp_after==FOJ_BATTLE_HERO_MAX_HP-
                                     FOJ_BATTLE_GUARDED_DAMAGE);
    assert(foj_battle_end_turn(&b)==prediction.event);
    assert(b.hero_hp==prediction.hero_hp_after);
    assert(!b.guarded_this_turn && !b.attacked_this_turn);
    assert(foj_battle_end_turn(&b)==FOJ_BATTLE_ENEMY_ATTACKED);
    assert(b.hero_hp==FOJ_BATTLE_HERO_MAX_HP-
                      FOJ_BATTLE_GUARDED_DAMAGE-FOJ_BATTLE_ENEMY_DAMAGE);
}

static void test_guard_consumes_attack_but_not_move(void) {
    FojBattle b;
    foj_battle_init(&b);
    assert(foj_battle_confirm(&b)==FOJ_BATTLE_SELECTED);
    assert(foj_battle_guard(&b)==FOJ_BATTLE_REJECTED);
    assert(!b.attacked_this_turn && !b.guarded_this_turn);
    assert(foj_battle_cancel(&b)==FOJ_BATTLE_CANCELED);
    assert(foj_battle_guard(&b)==FOJ_BATTLE_GUARDED);
    assert(foj_battle_guard(&b)==FOJ_BATTLE_REJECTED);
    assert(foj_battle_confirm(&b)==FOJ_BATTLE_SELECTED);
    foj_battle_move_cursor(&b,1,0);
    assert(foj_battle_confirm(&b)==FOJ_BATTLE_MOVED);
    assert(b.moved_this_turn && b.guarded_this_turn);
    b.map.hero_x=5; b.map.hero_y=2;
    b.map.enemy_x=6; b.map.enemy_y=2;
    b.map.cursor_x=6; b.map.cursor_y=2;
    assert(foj_battle_attack(&b)==FOJ_BATTLE_REJECTED);
    assert(b.enemy_hp==FOJ_BATTLE_ENEMY_MAX_HP);
    assert(foj_battle_end_turn(&b)==FOJ_BATTLE_ENEMY_ATTACKED);
    assert(!b.guarded_this_turn && !b.moved_this_turn);
}

static void test_guard_expiry_when_enemy_cannot_reach(void) {
    FojBattle b;
    foj_battle_init(&b);
    for (int y=0;y<FOJ_HEIGHT;++y)
        for (int x=0;x<FOJ_WIDTH;++x)
            if ((x!=b.map.hero_x || y!=b.map.hero_y) &&
                (x!=b.map.enemy_x || y!=b.map.enemy_y))
                b.map.cells[y][x].blocked=true;
    assert(foj_battle_guard(&b)==FOJ_BATTLE_GUARDED);
    assert(foj_battle_end_turn(&b)==FOJ_BATTLE_TURN_ENDED);
    assert(!b.guarded_this_turn);
    assert(b.hero_hp==FOJ_BATTLE_HERO_MAX_HP);
    assert(foj_battle_guard(&b)==FOJ_BATTLE_GUARDED);
}

static void test_guard_lethal_boundary_and_terminal_refusal(void) {
    FojBattle b;
    foj_battle_init(&b);
    b.hero_hp=FOJ_BATTLE_GUARDED_DAMAGE;
    b.map.hero_x=5; b.map.hero_y=2;
    b.map.enemy_x=6; b.map.enemy_y=2;
    assert(foj_battle_guard(&b)==FOJ_BATTLE_GUARDED);
    FojEnemyTurnForecast prediction;
    assert(foj_battle_forecast_enemy_turn(&b,&prediction));
    assert(prediction.event==FOJ_BATTLE_DEFEAT);
    assert(prediction.hero_hp_after==0);
    assert(foj_battle_end_turn(&b)==FOJ_BATTLE_DEFEAT);
    assert(b.outcome==FOJ_BATTLE_LOST && b.hero_hp==0);
    assert(foj_battle_guard(&b)==FOJ_BATTLE_REJECTED);
    assert(foj_battle_guard(NULL)==FOJ_BATTLE_REJECTED);
    foj_battle_init(&b);
    assert(!b.guarded_this_turn);
}

static void test_hero_attack_forecast_matches_real_attack_without_mutation(void) {
    FojBattle b;
    foj_battle_init(&b);
    b.map.hero_x=5; b.map.hero_y=2;
    b.map.enemy_x=6; b.map.enemy_y=2;
    b.map.cursor_x=6; b.map.cursor_y=2;
    FojBattle before=b;
    FojHeroAttackForecast forecast;
    assert(foj_battle_forecast_attack(&b,&forecast));
    assert(memcmp(&before,&b,sizeof(b))==0);
    assert(forecast.event==FOJ_BATTLE_ATTACKED);
    assert(forecast.enemy_hp_after==3);
    assert(forecast.outcome_after==FOJ_BATTLE_ONGOING);
    assert(foj_battle_attack(&b)==forecast.event);
    assert(b.enemy_hp==forecast.enemy_hp_after);
    assert(b.outcome==forecast.outcome_after);
    assert(!foj_battle_forecast_attack(&b,&forecast));
    assert(forecast.enemy_hp_after==0);
}

static void test_hero_attack_forecast_victory_and_bad_targets(void) {
    FojBattle b;
    foj_battle_init(&b);
    FojHeroAttackForecast forecast;
    assert(!foj_battle_forecast_attack(&b,&forecast)); /* distant */
    b.map.hero_x=5; b.map.hero_y=2;
    b.map.enemy_x=6; b.map.enemy_y=2;
    b.map.cursor_x=6; b.map.cursor_y=2;
    b.enemy_hp=3;
    assert(foj_battle_forecast_attack(&b,&forecast));
    assert(forecast.event==FOJ_BATTLE_VICTORY);
    assert(forecast.enemy_hp_after==0);
    assert(forecast.outcome_after==FOJ_BATTLE_WON);
    assert(foj_battle_attack(&b)==FOJ_BATTLE_VICTORY);
    assert(!foj_battle_forecast_attack(&b,&forecast));
    assert(!foj_battle_forecast_attack(NULL,&forecast));
    assert(!foj_battle_forecast_attack(&b,NULL));
}

static void test_hero_forecast_obeys_guard_and_elevation_constraints(void) {
    FojBattle b;
    foj_battle_init(&b);
    b.map.hero_x=5; b.map.hero_y=2;
    b.map.enemy_x=6; b.map.enemy_y=2;
    b.map.cursor_x=6; b.map.cursor_y=2;
    FojHeroAttackForecast forecast;
    b.map.selected=true;
    assert(!foj_battle_forecast_attack(&b,&forecast));
    b.map.selected=false;
    b.map.cells[2][6].elevation=3;
    assert(!foj_battle_forecast_attack(&b,&forecast));
    b.map.cells[2][6].elevation=1;
    assert(foj_battle_forecast_attack(&b,&forecast));
    assert(foj_battle_guard(&b)==FOJ_BATTLE_GUARDED);
    FojBattle before=b;
    assert(!foj_battle_forecast_attack(&b,&forecast));
    assert(memcmp(&b,&before,sizeof(b))==0);
    assert(forecast.enemy_hp_after==0);
    assert(b.enemy_hp==FOJ_BATTLE_ENEMY_MAX_HP);
}

static void test_undo_movement_restores_budget_and_cursor(void) {
    FojBattle b;
    foj_battle_init(&b);
    assert(foj_battle_cancel(&b)==FOJ_BATTLE_NO_ACTION);
    assert(foj_battle_confirm(&b)==FOJ_BATTLE_SELECTED);
    foj_battle_move_cursor(&b,1,0);
    assert(foj_battle_cancel(&b)==FOJ_BATTLE_CANCELED);
    assert(b.map.hero_x==1 && b.map.hero_y==2);
    assert(foj_battle_confirm(&b)==FOJ_BATTLE_SELECTED);
    foj_battle_move_cursor(&b,1,0);
    assert(foj_battle_confirm(&b)==FOJ_BATTLE_MOVED);
    assert(b.moved_this_turn && b.previous_hero_x==1 &&
           b.previous_hero_y==2);
    assert(b.map.hero_x==2 && b.map.hero_y==2);
    assert(foj_battle_cancel(&b)==FOJ_BATTLE_MOVE_UNDONE);
    assert(!b.moved_this_turn && !b.map.selected);
    assert(b.map.hero_x==1 && b.map.hero_y==2);
    assert(b.map.cursor_x==1 && b.map.cursor_y==2);
    assert(foj_battle_cancel(&b)==FOJ_BATTLE_NO_ACTION);
    assert(foj_battle_confirm(&b)==FOJ_BATTLE_SELECTED);
    foj_battle_move_cursor(&b,1,0);
    foj_battle_move_cursor(&b,1,0);
    assert(foj_battle_confirm(&b)==FOJ_BATTLE_MOVED);
    assert(b.map.hero_x==3 && b.map.hero_y==2);
}

static void test_undo_refuses_after_guard_attack_or_end_turn(void) {
    FojBattle b;
    foj_battle_init(&b);
    assert(foj_battle_confirm(&b)==FOJ_BATTLE_SELECTED);
    for(int i=0;i<4;++i)foj_battle_move_cursor(&b,1,0);
    assert(foj_battle_confirm(&b)==FOJ_BATTLE_MOVED);
    assert(foj_battle_guard(&b)==FOJ_BATTLE_GUARDED);
    FojBattle saved=b;
    assert(foj_battle_cancel(&b)==FOJ_BATTLE_REJECTED);
    assert(memcmp(&saved,&b,sizeof(b))==0);
    assert(foj_battle_end_turn(&b)==FOJ_BATTLE_ENEMY_ATTACKED);
    assert(!b.moved_this_turn);
    assert(foj_battle_cancel(&b)==FOJ_BATTLE_NO_ACTION);
    assert(b.map.hero_x==5 && b.map.hero_y==2);
    foj_battle_move_cursor(&b,1,0);
    assert(foj_battle_attack(&b)==FOJ_BATTLE_ATTACKED);
    assert(foj_battle_cancel(&b)==FOJ_BATTLE_NO_ACTION);
    foj_battle_init(&b);
    b.map.hero_x=5; b.map.hero_y=2;
    b.map.enemy_x=6; b.map.enemy_y=2;
    b.map.cursor_x=6; b.map.cursor_y=2;
    b.moved_this_turn=true;
    b.previous_hero_x=4;
    b.previous_hero_y=2;
    assert(foj_battle_attack(&b)==FOJ_BATTLE_ATTACKED);
    saved=b;
    assert(foj_battle_cancel(&b)==FOJ_BATTLE_REJECTED);
    assert(memcmp(&saved,&b,sizeof(b))==0);
}

static void test_undo_refuses_invalid_snapshot_and_post_battle(void) {
    FojBattle b;
    foj_battle_init(&b);
    b.moved_this_turn=true;
    b.previous_hero_x=FOJ_WIDTH;
    b.previous_hero_y=0;
    FojBattle before=b;
    assert(foj_battle_cancel(&b)==FOJ_BATTLE_REJECTED);
    assert(memcmp(&b,&before,sizeof(b))==0);
    b.previous_hero_x=2;
    b.previous_hero_y=1; /* synthetic blocked tile */
    before=b;
    assert(foj_battle_cancel(&b)==FOJ_BATTLE_REJECTED);
    assert(memcmp(&b,&before,sizeof(b))==0);
    b.outcome=FOJ_BATTLE_WON;
    assert(foj_battle_cancel(&b)==FOJ_BATTLE_REJECTED);
    assert(foj_battle_cancel(NULL)==FOJ_BATTLE_REJECTED);
}

static void test_undo_forecast_reverts_to_original_position(void) {
    FojBattle b;
    foj_battle_init(&b);
    FojEnemyTurnForecast baseline;
    assert(foj_battle_forecast_enemy_turn(&b,&baseline));
    assert(foj_battle_confirm(&b)==FOJ_BATTLE_SELECTED);
    for (int i=0;i<4;++i)foj_battle_move_cursor(&b,1,0);
    assert(foj_battle_confirm(&b)==FOJ_BATTLE_MOVED);
    FojEnemyTurnForecast moved;
    assert(foj_battle_forecast_enemy_turn(&b,&moved));
    assert(moved.hero_hp_after < baseline.hero_hp_after);
    assert(foj_battle_cancel(&b)==FOJ_BATTLE_MOVE_UNDONE);
    FojEnemyTurnForecast restored;
    const FojBattle before=b;
    assert(foj_battle_forecast_enemy_turn(&b,&restored));
    assert(memcmp(&before,&b,sizeof(b))==0);
    assert(restored.hero_hp_after==baseline.hero_hp_after);
    assert(restored.enemy_x_after==baseline.enemy_x_after);
    assert(restored.enemy_y_after==baseline.enemy_y_after);
}

static void test_null_arguments(void) {
    foj_battle_init(NULL);
    foj_battle_move_cursor(NULL,1,0);
    assert(foj_battle_confirm(NULL)==FOJ_BATTLE_REJECTED);
    assert(foj_battle_cancel(NULL)==FOJ_BATTLE_REJECTED);
    assert(foj_battle_attack(NULL)==FOJ_BATTLE_REJECTED);
    assert(foj_battle_end_turn(NULL)==FOJ_BATTLE_REJECTED);
}

int main(void) {
    test_init_and_confirm_move_budget();
    test_adjacent_attack_and_victory();
    test_invalid_targets_and_height_range();
    test_enemy_moves_and_attacks_deterministically();
    test_defeat_and_reset();
    test_impassable_enemy_and_turn_saturation();
    test_full_controller_style_playthrough_to_victory();
    test_forecast_is_pure_and_matches_actual_turns();
    test_forecast_defeat_no_mutation_and_nulls();
    test_forecast_immobile_enemy_and_saturated_clock();
    test_forecast_refreshes_after_hero_reposition();
    test_guard_halves_damage_and_expires();
    test_guard_consumes_attack_but_not_move();
    test_guard_expiry_when_enemy_cannot_reach();
    test_guard_lethal_boundary_and_terminal_refusal();
    test_hero_attack_forecast_matches_real_attack_without_mutation();
    test_hero_attack_forecast_victory_and_bad_targets();
    test_hero_forecast_obeys_guard_and_elevation_constraints();
    test_undo_movement_restores_budget_and_cursor();
    test_undo_refuses_after_guard_attack_or_end_turn();
    test_undo_refuses_invalid_snapshot_and_post_battle();
    test_undo_forecast_reverts_to_original_position();
    test_null_arguments();
    puts("Stage217 synthetic tactical battle: twenty-three scenarios passed");
    return 0;
}
