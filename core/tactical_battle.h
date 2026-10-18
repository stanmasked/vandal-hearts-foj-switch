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
    FOJ_BATTLE_ENEMY_DAMAGE = 2,
    FOJ_BATTLE_GUARDED_DAMAGE = 1
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
    FOJ_BATTLE_MOVE_UNDONE,
    FOJ_BATTLE_CANCELED,
    FOJ_BATTLE_ATTACKED,
    FOJ_BATTLE_GUARDED,
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
    uint8_t previous_hero_x;
    uint8_t previous_hero_y;
    bool attacked_this_turn;
    bool guarded_this_turn;
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

/* Non-committing X-action forecast: uses the exact attack rules on a
 * temporary copy, not a second damage or attack-range implementation. */
typedef struct {
    FojBattleEvent event;
    uint8_t enemy_hp_after;
    FojBattleOutcome outcome_after;
} FojHeroAttackForecast;

bool foj_battle_forecast_attack(const FojBattle *battle,
                                FojHeroAttackForecast *forecast);

/* While A has selected the hero, preview each legal movement target by
 * simulating the exact NEXT enemy turn on a temporary battle copy.
 * This shows invented tactical danger only; COLL channels and PS3
 * combat rules do not enter the calculation. */
typedef struct {
    uint8_t can_move[FOJ_HEIGHT][FOJ_WIDTH];
    uint8_t incoming_damage[FOJ_HEIGHT][FOJ_WIDTH];
    uint8_t enemy_x_after[FOJ_HEIGHT][FOJ_WIDTH];
    uint8_t enemy_y_after[FOJ_HEIGHT][FOJ_WIDTH];
} FojBattleThreatPreview;

bool foj_battle_preview_movement_threat(const FojBattle *battle,
                                       FojBattleThreatPreview *preview);

/* Optional caller-owned cache for an entire selected-movement risk map.
 * Only cursor_x/y may change between hits; all other game/terrain fields
 * are part of the key. No globals or stale predictions across turns.
 * Counters are instrumentation: one calculation for each cache miss. */
typedef struct {
    bool valid;
    FojBattle key;
    FojBattleThreatPreview preview;
    uint32_t calculations;
    uint32_t hits;
} FojBattleThreatCache;

void foj_battle_threat_cache_init(FojBattleThreatCache *cache);
bool foj_battle_preview_movement_threat_cached(FojBattleThreatCache *cache,
                                               const FojBattle *battle,
                                               FojBattleThreatPreview *preview);

void foj_battle_init(FojBattle *battle);
void foj_battle_move_cursor(FojBattle *battle, int dx, int dy);
FojBattleEvent foj_battle_confirm(FojBattle *battle);
/* B cancels a selection, or undoes a move before attack/guard/Y. */
FojBattleEvent foj_battle_cancel(FojBattle *battle);
FojBattleEvent foj_battle_attack(FojBattle *battle);
/* Guard consumes the hero's attack for this turn, not their move. */
FojBattleEvent foj_battle_guard(FojBattle *battle);
FojBattleEvent foj_battle_end_turn(FojBattle *battle);

#endif
