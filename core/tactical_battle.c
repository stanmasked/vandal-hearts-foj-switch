#include "tactical_battle.h"

#include <limits.h>
#include <stddef.h>
#include <string.h>

/* Fixed neighbor order for deterministic tie-breaking: N, E, S, W. */
static const int step_x[4] = {0, 1, 0, -1};
static const int step_y[4] = {-1, 0, 1, 0};

static bool walkable(const FojDemo *map, int x, int y, int nx, int ny) {
    if (!foj_in_bounds(x, y) || !foj_in_bounds(nx, ny) ||
        map->cells[ny][nx].blocked) return false;
    const int delta = (int)map->cells[ny][nx].elevation -
                      (int)map->cells[y][x].elevation;
    return delta >= -FOJ_MAX_STEP_HEIGHT && delta <= FOJ_MAX_STEP_HEIGHT;
}

static bool adjacent(const FojDemo *map) {
    if (!foj_in_bounds(map->hero_x, map->hero_y) ||
        !foj_in_bounds(map->enemy_x, map->enemy_y)) return false;
    int dx = map->hero_x - map->enemy_x;
    int dy = map->hero_y - map->enemy_y;
    if (dx < 0) dx = -dx;
    if (dy < 0) dy = -dy;
    if (dx + dy != 1) return false;
    return walkable(map, map->hero_x, map->hero_y,
                    map->enemy_x, map->enemy_y);
}

/* BFS from hero to enemy over invented height-map. Entire board is
 * bounded to 48 cells and there are no heap allocations. Returns false
 * if no legal step toward the hero exists; enemy cannot enter hero cell. */
static bool enemy_advance(FojDemo *map) {
    if (!foj_in_bounds(map->hero_x, map->hero_y) ||
        !foj_in_bounds(map->enemy_x, map->enemy_y)) return false;

    uint8_t distances[FOJ_HEIGHT][FOJ_WIDTH];
    memset(distances, FOJ_UNREACHABLE, sizeof(distances));
    int queue_x[FOJ_TILE_COUNT], queue_y[FOJ_TILE_COUNT];
    unsigned front = 0, back = 0;
    distances[map->hero_y][map->hero_x] = 0;
    queue_x[back] = map->hero_x;
    queue_y[back++] = map->hero_y;

    while (front < back) {
        int x = queue_x[front], y = queue_y[front++];
        for (unsigned dir = 0; dir < 4; ++dir) {
            int nx = x + step_x[dir], ny = y + step_y[dir];
            if (!walkable(map, x, y, nx, ny) ||
                distances[ny][nx] != FOJ_UNREACHABLE) continue;
            distances[ny][nx] = (uint8_t)(distances[y][x] + 1u);
            queue_x[back] = nx;
            queue_y[back++] = ny;
        }
    }

    const uint8_t cost = distances[map->enemy_y][map->enemy_x];
    if (cost == FOJ_UNREACHABLE || cost <= 1u) return false;
    for (unsigned dir = 0; dir < 4; ++dir) {
        int nx = map->enemy_x + step_x[dir];
        int ny = map->enemy_y + step_y[dir];
        if (walkable(map, map->enemy_x, map->enemy_y, nx, ny) &&
            distances[ny][nx] == (uint8_t)(cost - 1u) &&
            !(nx == map->hero_x && ny == map->hero_y)) {
            map->enemy_x = nx;
            map->enemy_y = ny;
            return true;
        }
    }
    return false;
}

void foj_battle_init(FojBattle *battle) {
    if (!battle) return;
    memset(battle, 0, sizeof(*battle));
    foj_demo_init(&battle->map);
    battle->hero_hp = FOJ_BATTLE_HERO_MAX_HP;
    battle->enemy_hp = FOJ_BATTLE_ENEMY_MAX_HP;
    battle->turn_number = 1;
    battle->outcome = FOJ_BATTLE_ONGOING;
}

void foj_battle_move_cursor(FojBattle *battle, int dx, int dy) {
    if (battle && battle->outcome == FOJ_BATTLE_ONGOING)
        foj_move_cursor(&battle->map, dx, dy);
}

FojBattleEvent foj_battle_confirm(FojBattle *battle) {
    if (!battle || battle->outcome != FOJ_BATTLE_ONGOING)
        return FOJ_BATTLE_REJECTED;
    if (battle->moved_this_turn) return FOJ_BATTLE_REJECTED;
    FojAction action = foj_press_a(&battle->map);
    if (action == FOJ_ACTION_SELECTED) return FOJ_BATTLE_SELECTED;
    if (action == FOJ_ACTION_MOVED) {
        battle->moved_this_turn = true;
        return FOJ_BATTLE_MOVED;
    }
    return action == FOJ_ACTION_NONE ? FOJ_BATTLE_NO_ACTION :
           FOJ_BATTLE_REJECTED;
}

FojBattleEvent foj_battle_cancel(FojBattle *battle) {
    if (!battle || battle->outcome != FOJ_BATTLE_ONGOING)
        return FOJ_BATTLE_REJECTED;
    return foj_press_b(&battle->map) == FOJ_ACTION_CANCELED ?
           FOJ_BATTLE_CANCELED : FOJ_BATTLE_NO_ACTION;
}

FojBattleEvent foj_battle_attack(FojBattle *battle) {
    if (!battle || battle->outcome != FOJ_BATTLE_ONGOING ||
        battle->attacked_this_turn || battle->map.selected ||
        battle->map.cursor_x != battle->map.enemy_x ||
        battle->map.cursor_y != battle->map.enemy_y ||
        !adjacent(&battle->map)) return FOJ_BATTLE_REJECTED;

    battle->attacked_this_turn = true;
    if (battle->enemy_hp <= FOJ_BATTLE_HERO_DAMAGE) {
        battle->enemy_hp = 0;
        battle->outcome = FOJ_BATTLE_WON;
        return FOJ_BATTLE_VICTORY;
    }
    battle->enemy_hp -= FOJ_BATTLE_HERO_DAMAGE;
    return FOJ_BATTLE_ATTACKED;
}

FojBattleEvent foj_battle_guard(FojBattle *battle) {
    if (!battle || battle->outcome != FOJ_BATTLE_ONGOING ||
        battle->attacked_this_turn || battle->map.selected)
        return FOJ_BATTLE_REJECTED;
    battle->attacked_this_turn = true;
    battle->guarded_this_turn = true;
    return FOJ_BATTLE_GUARDED;
}

FojBattleEvent foj_battle_end_turn(FojBattle *battle) {
    if (!battle || battle->outcome != FOJ_BATTLE_ONGOING)
        return FOJ_BATTLE_REJECTED;
    const bool guarded = battle->guarded_this_turn;
    battle->map.selected = false;
    battle->moved_this_turn = false;
    battle->attacked_this_turn = false;
    battle->guarded_this_turn = false;
    if (battle->turn_number < UINT16_MAX) ++battle->turn_number;
    bool advanced = false;
    if (!adjacent(&battle->map)) advanced = enemy_advance(&battle->map);
    if (!adjacent(&battle->map))
        return advanced ? FOJ_BATTLE_ENEMY_MOVED : FOJ_BATTLE_TURN_ENDED;

    const uint8_t damage = guarded ?
        FOJ_BATTLE_GUARDED_DAMAGE : FOJ_BATTLE_ENEMY_DAMAGE;
    if (battle->hero_hp <= damage) {
        battle->hero_hp = 0;
        battle->outcome = FOJ_BATTLE_LOST;
        return FOJ_BATTLE_DEFEAT;
    }
    battle->hero_hp = (uint8_t)(battle->hero_hp - damage);
    return FOJ_BATTLE_ENEMY_ATTACKED;
}

bool foj_battle_forecast_enemy_turn(const FojBattle *battle,
                                     FojEnemyTurnForecast *forecast) {
    if (!forecast) return false;
    memset(forecast, 0, sizeof(*forecast));
    if (!battle || battle->outcome != FOJ_BATTLE_ONGOING)
        return false;

    /* Single code path for real turn and prediction. Keeping the copy
     * local prevents accidentally resetting action flags in the game. */
    FojBattle imagined = *battle;
    const FojBattleEvent action = foj_battle_end_turn(&imagined);
    if (action == FOJ_BATTLE_REJECTED) return false;
    forecast->event = action;
    forecast->enemy_x_after = imagined.map.enemy_x;
    forecast->enemy_y_after = imagined.map.enemy_y;
    forecast->hero_hp_after = imagined.hero_hp;
    forecast->turn_after = imagined.turn_number;
    forecast->outcome_after = imagined.outcome;
    return true;
}

bool foj_battle_forecast_attack(const FojBattle *battle,
                                FojHeroAttackForecast *forecast) {
    if (!forecast) return false;
    memset(forecast, 0, sizeof(*forecast));
    if (!battle || battle->outcome != FOJ_BATTLE_ONGOING) return false;

    /* Only a copy may receive the speculative attack. This guarantees
     * guard, elevation, cursor and used-attack checks match the X action. */
    FojBattle predicted = *battle;
    const FojBattleEvent event = foj_battle_attack(&predicted);
    if (event != FOJ_BATTLE_ATTACKED && event != FOJ_BATTLE_VICTORY)
        return false;
    forecast->event = event;
    forecast->enemy_hp_after = predicted.enemy_hp;
    forecast->outcome_after = predicted.outcome;
    return true;
}
