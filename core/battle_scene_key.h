#ifndef FOJ_BATTLE_SCENE_KEY_H
#define FOJ_BATTLE_SCENE_KEY_H
/*
 * Scene-key equality for synthetic battle measurement probes only.
 * Compare every named gameplay field, NEVER struct padding bytes.
 * Not an original PS3 gameplay/resource representation.
 */
#include "tactical_battle.h"

static inline bool foj_battle_scene_key_equal(const FojBattle *a,
                                               const FojBattle *b) {
    if (!a || !b) return false;
    const FojDemo *x=&a->map,*y=&b->map;
    if (x->hero_x!=y->hero_x || x->hero_y!=y->hero_y ||
        x->enemy_x!=y->enemy_x || x->enemy_y!=y->enemy_y ||
        x->cursor_x!=y->cursor_x || x->cursor_y!=y->cursor_y ||
        x->selected!=y->selected ||
        a->hero_hp!=b->hero_hp || a->enemy_hp!=b->enemy_hp ||
        a->moved_this_turn!=b->moved_this_turn ||
        a->previous_hero_x!=b->previous_hero_x ||
        a->previous_hero_y!=b->previous_hero_y ||
        a->attacked_this_turn!=b->attacked_this_turn ||
        a->guarded_this_turn!=b->guarded_this_turn ||
        a->turn_number!=b->turn_number || a->outcome!=b->outcome)
        return false;
    for (int row=0;row<FOJ_HEIGHT;++row)
        for (int col=0;col<FOJ_WIDTH;++col)
            if (x->cells[row][col].elevation !=
                y->cells[row][col].elevation ||
                x->cells[row][col].blocked !=
                y->cells[row][col].blocked)
                return false;
    return true;
}
#endif
