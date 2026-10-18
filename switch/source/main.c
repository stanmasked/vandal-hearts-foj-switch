/*
 * Vandal Hearts: Flames of Judgment — Nintendo Switch research bring-up.
 *
 * Invented 8x6 tactical grid with elevation, walls and movement ranges.
 * Not a conversion or implementation of the original PS3 game.
 * No copyrighted assets or Konami executable code.
 */
#include <switch.h>
#include <stdio.h>
#include <stdlib.h>

#include "coll_grid.h"
#include "coll_battle_window.h"
#include "local_coll_window.h"

#include "tactical_battle.h"
#include "battle_replay.h"

/* The local COLL crop is a research readout only. Gameplay stays
 * invented and is completely independent of these six raw channels. */
static FojCollBattleWindow local_window;
static bool has_local_window;

static bool load_private_coll(void) {
    return foj_local_coll_load_path(
        "sdmc:/switch/foj/maps/map1-1.coll", &local_window);
}

static const char *status_label(FojBattleEvent action) {
    switch (action) {
        case FOJ_BATTLE_SELECTED: return "Hero selected";
        case FOJ_BATTLE_MOVED: return "Hero moved";
        case FOJ_BATTLE_MOVE_UNDONE: return "Hero move undone";
        case FOJ_BATTLE_CANCELED: return "Selection canceled";
        case FOJ_BATTLE_ATTACKED: return "Attack hit!";
        case FOJ_BATTLE_GUARDED: return "Guard stance set";
        case FOJ_BATTLE_ENEMY_MOVED: return "Enemy advanced";
        case FOJ_BATTLE_ENEMY_ATTACKED: return "Enemy attacked!";
        case FOJ_BATTLE_TURN_ENDED: return "Turn ended";
        case FOJ_BATTLE_VICTORY: return "Victory (synthetic)";
        case FOJ_BATTLE_DEFEAT: return "Defeat (synthetic)";
        case FOJ_BATTLE_REJECTED: return "Illegal action";
        default: return "Select hero with A";
    }
}

static void draw_scene(const FojBattle *battle, FojBattleEvent action, int diagnostic_channel,
                       const FojBattleReplay *replay, bool show_threat_preview) {
    const FojDemo *state = &battle->map;
    uint8_t reach[FOJ_HEIGHT][FOJ_WIDTH];
    foj_reachability(state, reach);

    /* ANSI clear and home are supported by the homebrew console. */
    printf("\x1b[2J\x1b[H");
    printf("Vandal Hearts: Flames of Judgment\n");
    printf("Independent Nintendo Switch research NRO\n");
    printf("========================================\n");
    printf("SYNTHETIC MAP ONLY -- PS3 GAME NOT RUNNING\n\n");
    printf("D-Pad: cursor / A: select+move / X: attack\n");
    printf("B: cancel selection / undo move before attack or guard\n");
    printf("Y: end turn / MINUS: restart / PLUS: exit\n");
    printf("ZR: guard (uses attack, reduces next enemy hit)\n");
    printf("Right stick: toggle movement danger preview (%s)\n",
           show_threat_preview ? "ON" : "OFF");
    printf("L/R: raw COLL diagnostic channel (0-5), if provided locally\n");
    printf("H hero, E enemy, # wall, 0-2 height\n");
    printf("+ reachable after selecting H, < cursor\n\n");

    for (int y = 0; y < FOJ_HEIGHT; ++y) {
        printf("  ");
        for (int x = 0; x < FOJ_WIDTH; ++x) {
            char tile = (char)('0' + state->cells[y][x].elevation);
            if (state->cells[y][x].blocked) tile = '#';
            if (state->selected && reach[y][x] != FOJ_UNREACHABLE &&
                !(x == state->hero_x && y == state->hero_y)) tile = '+';
            if (battle->enemy_hp > 0 &&
                x == state->enemy_x && y == state->enemy_y) tile = 'E';
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
    FojEnemyTurnForecast forecast;
    if (foj_battle_forecast_enemy_turn(battle, &forecast)) {
        printf("If Y now: enemy -> (%d,%d), hero HP -> %u, %s\n",
               forecast.enemy_x_after, forecast.enemy_y_after,
               (unsigned)forecast.hero_hp_after, status_label(forecast.event));
    } else {
        puts("Enemy forecast unavailable: battle already ended.");
    }
    FojBattleThreatPreview threat;
    if (show_threat_preview &&
        foj_battle_preview_movement_threat(battle,&threat) &&
        foj_in_bounds(state->cursor_x,state->cursor_y)) {
        const int x=state->cursor_x, y=state->cursor_y;
        if (threat.can_move[y][x])
            printf("Move to (%d,%d): damage %u HP, enemy next (%u,%u)\n",
                   x,y,(unsigned)threat.incoming_damage[y][x],
                   (unsigned)threat.enemy_x_after[y][x],
                   (unsigned)threat.enemy_y_after[y][x]);
        else
            puts("Move to cursor: unavailable destination.");
    }
    printf("Guard=%s\n",battle->guarded_this_turn ? "active":"off");
    FojHeroAttackForecast attack_view;
    if (foj_battle_forecast_attack(battle,&attack_view))
        printf("If X now: enemy HP -> %u, %s\n",
               (unsigned)attack_view.enemy_hp_after,
               status_label(attack_view.event));
    if (battle->moved_this_turn && !battle->attacked_this_turn)
        puts("B can undo your previous move.");
    printf("Input replay: %u/%u, %s\n",
           (unsigned)replay->count, FOJ_REPLAY_MAX_INPUTS,
           foj_replay_matches(replay, battle) ? "VERIFIED" : "MISMATCH");
        printf("Move used=%s Attack used=%s\n",
           battle->moved_this_turn ? "yes":"no",
           battle->attacked_this_turn ? "yes":"no");
    printf("\nStatus: %s\n", status_label(action));
    printf("Hero=(%d,%d) Cursor=(%d,%d) Selected=%s\n",
           state->hero_x, state->hero_y,
           state->cursor_x, state->cursor_y,
           state->selected ? "yes" : "no");
    if (has_local_window && foj_in_bounds(state->cursor_x, state->cursor_y)) {
        const int tx=state->cursor_x, ty=state->cursor_y;
        if (diagnostic_channel < 4) {
            float value=0.0f;
            if (foj_coll_window_sample(&local_window,tx,ty,
                                         (unsigned)diagnostic_channel,&value))
                printf("LOCAL COLL RAW channel %d: (src %d,%d) = %.6g\n",
                       diagnostic_channel,tx+local_window.source_x,
                       ty+local_window.source_y,(double)value);
        } else {
            uint8_t value=0;
            if (foj_coll_window_flag(&local_window,tx,ty,
                                       (unsigned)(diagnostic_channel-4),&value))
                printf("LOCAL COLL RAW flag %d: (src %d,%d) = %u\n",
                       diagnostic_channel-4,tx+local_window.source_x,
                       ty+local_window.source_y,(unsigned)value);
        }
        puts("RAW RESEARCH DATA ONLY; DOES NOT AFFECT MOVEMENT OR COMBAT.");
    } else {
        puts("No private COLL window loaded. All terrain remains SYNTHETIC.");
    }
    consoleUpdate(NULL);
}

int main(int argc, char **argv) {
    (void)argc;
    (void)argv;

    consoleInit(NULL);
    has_local_window = load_private_coll();
    if (!has_local_window && R_SUCCEEDED(fsdevMountSdmc()))
        has_local_window = load_private_coll();
    int diagnostic_channel = 0;
    padConfigureInput(1, HidNpadStyleSet_NpadStandard);
    PadState pad;
    padInitializeDefault(&pad);

    FojBattle battle;
    foj_battle_init(&battle);
    FojBattleReplay replay;
    foj_replay_init(&replay);
    bool show_threat_preview=true;
    FojBattleEvent last = FOJ_BATTLE_NO_ACTION;
    draw_scene(&battle, last, diagnostic_channel, &replay, show_threat_preview);

    while (appletMainLoop()) {
        padUpdate(&pad);
        const u64 pressed = padGetButtonsDown(&pad);
        if (pressed & HidNpadButton_Plus) break;
        bool redraw = false;

        if (pressed & HidNpadButton_Up) {
            (void)foj_replay_record(&replay,&battle,FOJ_REPLAY_UP,&last);
            redraw = true;
        }
        if (pressed & HidNpadButton_Down) {
            (void)foj_replay_record(&replay,&battle,FOJ_REPLAY_DOWN,&last);
            redraw = true;
        }
        if (pressed & HidNpadButton_Left) {
            (void)foj_replay_record(&replay,&battle,FOJ_REPLAY_LEFT,&last);
            redraw = true;
        }
        if (pressed & HidNpadButton_Right) {
            (void)foj_replay_record(&replay,&battle,FOJ_REPLAY_RIGHT,&last);
            redraw = true;
        }
        if (pressed & HidNpadButton_A) {
            (void)foj_replay_record(&replay,&battle,FOJ_REPLAY_A,&last);
            redraw = true;
        }
        if (pressed & HidNpadButton_B) {
            (void)foj_replay_record(&replay,&battle,FOJ_REPLAY_B,&last);
            redraw = true;
        }
        if (pressed & HidNpadButton_X) {
            (void)foj_replay_record(&replay,&battle,FOJ_REPLAY_X,&last);
            redraw = true;
        }
        if (pressed & HidNpadButton_ZR) {
            (void)foj_replay_record(&replay,&battle,FOJ_REPLAY_ZR,&last);
            redraw = true;
        }
        if (pressed & HidNpadButton_Y) {
            (void)foj_replay_record(&replay,&battle,FOJ_REPLAY_Y,&last);
            redraw = true;
        }
        if (pressed & HidNpadButton_Minus) {
            (void)foj_replay_record(&replay,&battle,FOJ_REPLAY_RESET,&last);
            redraw = true;
        }
        if (pressed & HidNpadButton_StickR) {
            show_threat_preview = !show_threat_preview;
            redraw = true;
        }
        if (pressed & HidNpadButton_R) {
            diagnostic_channel = (diagnostic_channel + 1) % 6;
            redraw = true;
        }
        if (pressed & HidNpadButton_L) {
            diagnostic_channel = (diagnostic_channel + 5) % 6;
            redraw = true;
        }
        if (redraw) draw_scene(&battle, last, diagnostic_channel, &replay, show_threat_preview);
        consoleUpdate(NULL);
    }
    consoleExit(NULL);
    return 0;
}
