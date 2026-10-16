/* Host-side unit tests of invented mechanics, not original game behavior. */
#include "tactical_demo.h"
#include <assert.h>
#include <stdio.h>

static void test_initial_state_and_reachability(void) {
    FojDemo s;
    foj_demo_init(&s);
    assert(s.hero_x == 1 && s.hero_y == 2);
    assert(s.enemy_x == 6 && s.enemy_y == 3);
    assert(s.cursor_x == 1 && s.cursor_y == 2 && !s.selected);
    uint8_t d[FOJ_HEIGHT][FOJ_WIDTH];
    foj_reachability(&s, d);
    assert(d[2][1] == 0);
    assert(d[2][2] == 1); /* ramp to +1 */
    assert(d[2][3] == 2); /* plateau to +2 */
    assert(d[1][2] == FOJ_UNREACHABLE); /* wall */
    assert(d[3][2] == FOJ_UNREACHABLE); /* wall */
    assert(d[3][6] == FOJ_UNREACHABLE); /* enemy */
    assert(d[5][7] == FOJ_UNREACHABLE); /* exceeds move budget */
}

static void test_selection_move_and_cancel(void) {
    FojDemo s;
    foj_demo_init(&s);
    assert(foj_press_a(&s) == FOJ_ACTION_SELECTED);
    assert(s.selected);
    foj_move_cursor(&s, 1, 0);
    assert(foj_press_a(&s) == FOJ_ACTION_MOVED);
    assert(s.hero_x == 2 && s.hero_y == 2 && !s.selected);

    assert(foj_press_a(&s) == FOJ_ACTION_SELECTED);
    assert(foj_press_b(&s) == FOJ_ACTION_CANCELED);
    assert(!s.selected);
    assert(foj_press_b(&s) == FOJ_ACTION_NONE);
}

static void test_reject_blocked_enemy_and_far_move(void) {
    FojDemo s;
    foj_demo_init(&s);
    assert(foj_press_a(&s) == FOJ_ACTION_SELECTED);
    s.cursor_x = 2;
    s.cursor_y = 1;
    assert(foj_press_a(&s) == FOJ_ACTION_REJECTED);
    assert(s.hero_x == 1 && s.hero_y == 2 && s.selected);
    s.cursor_x = 7;
    s.cursor_y = 5;
    assert(foj_press_a(&s) == FOJ_ACTION_REJECTED);

    s.hero_x = 5;
    s.hero_y = 3;
    s.cursor_x = 6;
    s.cursor_y = 3;
    assert(foj_press_a(&s) == FOJ_ACTION_REJECTED);
    assert(s.hero_x == 5 && s.hero_y == 3);
}

static void test_cliffs_and_no_selection(void) {
    FojDemo s;
    foj_demo_init(&s);
    s.cursor_x = 3;
    s.cursor_y = 2;
    assert(foj_press_a(&s) == FOJ_ACTION_NONE);
    assert(!s.selected);
    /* Make a height-3 cliff that cannot be climbed in one step. */
    s.cells[2][2].elevation = 3;
    uint8_t d[FOJ_HEIGHT][FOJ_WIDTH];
    foj_reachability(&s, d);
    assert(d[2][2] == FOJ_UNREACHABLE);
    assert(d[2][3] == FOJ_UNREACHABLE);
}

static void test_cursor_clamps_to_board(void) {
    FojDemo s;
    foj_demo_init(&s);
    foj_move_cursor(&s, -100, -100);
    assert(s.cursor_x == 0 && s.cursor_y == 0);
    foj_move_cursor(&s, 100, 100);
    assert(s.cursor_x == FOJ_WIDTH - 1 && s.cursor_y == FOJ_HEIGHT - 1);
    assert(!foj_in_bounds(-1, 0));
    assert(!foj_in_bounds(FOJ_WIDTH, 0));
}

int main(void) {
    test_initial_state_and_reachability();
    test_selection_move_and_cancel();
    test_reject_blocked_enemy_and_far_move();
    test_cliffs_and_no_selection();
    test_cursor_clamps_to_board();
    puts("Synthetic tactics tests passed (five scenarios)");
    return 0;
}
