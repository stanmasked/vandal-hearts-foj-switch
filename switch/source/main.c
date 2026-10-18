/*
 * Vandal Hearts: Flames of Judgment — Nintendo Switch research bring-up.
 *
 * Invented 8x6 tactical grid with elevation, walls and movement ranges.
 * Not a conversion or implementation of the original PS3 game.
 * No copyrighted assets or Konami executable code.
 */
#include <switch.h>
#include <stdio.h>

#include "tactical_battle.h"

static const char *status_label(FojBattleEvent action) {
    switch (action) {
        case FOJ_BATTLE_SELECTED: return "Hero selected";
        case FOJ_BATTLE_MOVED: return "Hero moved";
        case FOJ_BATTLE_CANCELED: return "Selection canceled";
        case FOJ_BATTLE_ATTACKED: return "Attack hit!";
        case FOJ_BATTLE_ENEMY_MOVED: return "Enemy advanced";
        case FOJ_BATTLE_ENEMY_ATTACKED: return "Enemy attacked!";
        case FOJ_BATTLE_TURN_ENDED: return "Turn ended";
        case FOJ_BATTLE_VICTORY: return "Victory (synthetic)";
        case FOJ_BATTLE_DEFEAT: return "Defeat (synthetic)";
        case FOJ_BATTLE_REJECTED: return "Illegal action";
        default: return "Select hero with A";
    }
}

static void draw_scene(const FojBattle *battle, FojBattleEvent action) {
    const FojDemo *state = &battle->map;
    uint8_t reach[FOJ_HEIGHT][FOJ_WIDTH];
    foj_reachability(state, reach);

    /* ANSI clear and home are supported by the homebrew console. */
    printf("\x1b[2J\x1b[H");
    printf("Vandal Hearts: Flames of Judgment\n");
    printf("Independent Nintendo Switch research NRO\n");
    printf("========================================\n");
    printf("SYNTHETIC MAP ONLY -- PS3 GAME NOT RUNNING\n\n");
    printf("D-Pad: move cursor / A: select or move\n");
    printf("B: cancel selection / PLUS: exit\n");
    printf("H hero, E enemy, # wall, 0-2 height\n");
    printf("+ reachable after selecting H, < cursor\n\n");

    for (int y = 0; y < FOJ_HEIGHT; ++y) {
        printf("  ");
        for (int x = 0; x < FOJ_WIDTH; ++x) {
            char tile = (char)('0' + state->cells[y][x].elevation);
            if (state->cells[y][x].blocked) tile = '#';
            if (state->selected && reach[y][x] != FOJ_UNREACHABLE &&
                !(x == state->hero_x && y == state->hero_y)) tile = '+';
            if (x == state->enemy_x && y == state->enemy_y) tile = 'E';
            if (x == state->hero_x && y == state->hero_y) tile = 'H';
            printf("%c%c ", tile,
                   x == state->cursor_x && y == state->cursor_y ? '<' : ' ');
        }
        printf("\n");
    }
    printf("\nTurn %u | Hero HP %u/%u | Enemy HP %u/%u\n",
           (unsigned)battle->turn_number, (unsigned)battle->hero_hp,
           FOJ_BATTLE_HERO_MAX_HP, (unsigned)battle->enemy_hp,
           FOJ_BATTLE_ENEMY_MAX_HP);
    printf("Move used=%s Attack used=%s\n",
           battle->moved_this_turn ? "yes":"no",
           battle->attacked_this_turn ? "yes":"no");
    printf("\nStatus: %s\n", status_label(action));
    printf("Hero=(%d,%d) Cursor=(%d,%d) Selected=%s\n",
           state->hero_x, state->hero_y,
           state->cursor_x, state->cursor_y,
           state->selected ? "yes" : "no");
    consoleUpdate(NULL);
}

int main(int argc, char **argv) {
    (void)argc;
    (void)argv;

    consoleInit(NULL);
    padConfigureInput(1, HidNpadStyleSet_NpadStandard);
    PadState pad;
    padInitializeDefault(&pad);

    FojBattle battle;
    foj_battle_init(&battle);
    FojBattleEvent last = FOJ_BATTLE_NO_ACTION;
    draw_scene(&battle, last);

    while (appletMainLoop()) {
        padUpdate(&pad);
        const u64 pressed = padGetButtonsDown(&pad);
        if (pressed & HidNpadButton_Plus) break;
        bool redraw = false;

        if (pressed & HidNpadButton_Up) {
            foj_battle_move_cursor(&battle, 0, -1);
            redraw = true;
        }
        if (pressed & HidNpadButton_Down) {
            foj_battle_move_cursor(&battle, 0, 1);
            redraw = true;
        }
        if (pressed & HidNpadButton_Left) {
            foj_battle_move_cursor(&battle, -1, 0);
            redraw = true;
        }
        if (pressed & HidNpadButton_Right) {
            foj_battle_move_cursor(&battle, 1, 0);
            redraw = true;
        }
        if (pressed & HidNpadButton_A) {
            last = foj_battle_confirm(&battle);
            redraw = true;
        }
        if (pressed & HidNpadButton_B) {
            last = foj_battle_cancel(&battle);
            redraw = true;
        }
        if (pressed & HidNpadButton_X) {
            last = foj_battle_attack(&battle);
            redraw = true;
        }
        if (pressed & HidNpadButton_Y) {
            last = foj_battle_end_turn(&battle);
            redraw = true;
        }
        if (pressed & HidNpadButton_Minus) {
            foj_battle_init(&battle);
            last = FOJ_BATTLE_NO_ACTION;
            redraw = true;
        }
        if (redraw) draw_scene(&battle, last);
        consoleUpdate(NULL);
    }
    consoleExit(NULL);
    return 0;
}
