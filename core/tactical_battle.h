#ifndef FOJ_TACTICAL_BATTLE_H
#define FOJ_TACTICAL_BATTLE_H

/* Generated-only tactical prototype. No PS3 engine, assets, or rules. */
#include "tactical_demo.h"

#include <stdbool.h>
#include <stdint.h>

enum {
    FOJ_BATTLE_HERO_MAX_HP = 8,
    FOJ_BATTLE_ENEMY_MAX_HP = 6,
    FOJ_BATTLE_HERO_DAMAGE = 3,
    FOJ_BATTLE_ENEMY_DAMAGE = 2
};

typedef enum {
    FOJ_BATTLE_ONGOING = 0,
    FOJ_BATTLE_WON,
    FOJ_BATTLE_LOST
} FojBattleOutcome;

typedef enum {
    FOJ_BATTLE_NO_ACTION = 0,
    FOJ_BATTLE_SELECTED,
    FOJ_BATTLE_MOVED,
    FOJ_BATTLE_CANCELED,
    FOJ_BATTLE_ATTACKED,
    FOJ_BATTLE_ENEMY_MOVED,
    FOJ_BATTLE_ENEMY_ATTACKED,
    FOJ_BATTLE_TURN_ENDED,
    FOJ_BATTLE_VICTORY,
    FOJ_BATTLE_DEFEAT,
    FOJ_BATTLE_REJECTED
} FojBattleEvent;

typedef struct {
    FojDemo map;
    uint8_t hero_hp;
    uint8_t enemy_hp;
    bool moved_this_turn;
    bool attacked_this_turn;
    uint16_t turn_number;
    FojBattleOutcome outcome;
} FojBattle;

/* A read-only forecast of pressing Y now. Uses the same deterministic
 * enemy-turn rules as the real action, but never commits to the state.
 * No source-game AI or original-game attack parameters are asserted. */
typedef struct {
    FojBattleEvent event;
    int enemy_x_after;
    int enemy_y_after;
    uint8_t hero_hp_after;
    uint16_t turn_after;
    FojBattleOutcome outcome_after;
} FojEnemyTurnForecast;

bool foj_battle_forecast_enemy_turn(const FojBattle *battle,
                                     FojEnemyTurnForecast *forecast);

void foj_battle_init(FojBattle *battle);
void foj_battle_move_cursor(FojBattle *battle, int dx, int dy);
FojBattleEvent foj_battle_confirm(FojBattle *battle);
FojBattleEvent foj_battle_cancel(FojBattle *battle);
FojBattleEvent foj_battle_attack(FojBattle *battle);
FojBattleEvent foj_battle_end_turn(FojBattle *battle);

#endif
