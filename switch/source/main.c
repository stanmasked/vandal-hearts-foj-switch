/*
 * Vandal Hearts: Flames of Judgment — Nintendo Switch research bring-up.
 *
 * Invented 8x6 tactical grid with elevation, walls and movement ranges.
 * Not a conversion or implementation of the original PS3 game.
 * No copyrighted assets or Konami executable code.
 */
#include <switch.h>
#include <stdio.h>

#include "tactical_demo.h"

static const char *status_label(FojAction action) {
    switch (action) {
        case FOJ_ACTION_SELECTED: return "Unit selected";
        case FOJ_ACTION_MOVED: return "Move accepted";
        case FOJ_ACTION_REJECTED: return "Move rejected";
        case FOJ_ACTION_CANCELED: return "Selection canceled";
        default: return "Move cursor to H, press A";
    }
}

static void draw_scene(const FojDemo *state, FojAction action) {
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

    FojDemo state;
    foj_demo_init(&state);
    FojAction last = FOJ_ACTION_NONE;
    draw_scene(&state, last);

    while (appletMainLoop()) {
        padUpdate(&pad);
        const u64 pressed = padGetButtonsDown(&pad);
        if (pressed & HidNpadButton_Plus) break;
        bool redraw = false;

        if (pressed & HidNpadButton_Up) {
            foj_move_cursor(&state, 0, -1);
            redraw = true;
        }
        if (pressed & HidNpadButton_Down) {
            foj_move_cursor(&state, 0, 1);
            redraw = true;
        }
        if (pressed & HidNpadButton_Left) {
            foj_move_cursor(&state, -1, 0);
            redraw = true;
        }
        if (pressed & HidNpadButton_Right) {
            foj_move_cursor(&state, 1, 0);
            redraw = true;
        }
        if (pressed & HidNpadButton_A) {
            last = foj_press_a(&state);
            redraw = true;
        }
        if (pressed & HidNpadButton_B) {
            last = foj_press_b(&state);
            redraw = true;
        }
        if (redraw) draw_scene(&state, last);
        consoleUpdate(NULL);
    }
    consoleExit(NULL);
    return 0;
}
