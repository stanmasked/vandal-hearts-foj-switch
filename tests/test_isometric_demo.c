/* Deterministic host-side checks for a synthetic tile renderer. */
#include <assert.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "tactical_demo.h"
#include "isometric_demo.h"

static uint64_t fingerprint(const uint32_t *pixels, size_t count) {
    uint64_t hash = UINT64_C(1469598103934665603);
    for (size_t i = 0; i < count; ++i) {
        hash ^= pixels[i];
        hash *= UINT64_C(1099511628211);
    }
    return hash;
}

static void test_projection(void) {
    int x, y;
    foj_iso_project(1280, 720, 1, 2, 0, &x, &y);
    assert(x == 586 && y == 210);
    foj_iso_project(1280, 720, 1, 2, 2, &x, &y);
    assert(x == 586 && y == 174);
}

static void test_render_and_reachable_highlights(void) {
    const int width = 1280, height = 720;
    const size_t count = (size_t)width * (size_t)height;
    uint32_t *pixels = calloc(count, sizeof(*pixels));
    assert(pixels);
    FojDemo state;
    foj_demo_init(&state);

    foj_iso_render(&state, pixels, width, height, width);
    const uint64_t baseline = fingerprint(pixels, count);
    assert(pixels[0] == UINT32_C(0xff21130d)); /* background */
    size_t changed = 0;
    for (size_t i = 0; i < count; ++i) {
        if (pixels[i] != UINT32_C(0xff21130d)) ++changed;
    }
    assert(changed > 10000);

    state.selected = true;
    foj_iso_render(&state, pixels, width, height, width);
    assert(fingerprint(pixels, count) != baseline);

    state.cursor_x = 3;
    state.cursor_y = 2;
    foj_iso_render(&state, pixels, width, height, width);
    assert(fingerprint(pixels, count) != baseline);
    free(pixels);
}

static void test_selected_route_overlay_and_cancel(void) {
    const int width=1280,height=720;
    const size_t count=(size_t)width*(size_t)height;
    uint32_t *pixels=calloc(count,sizeof(*pixels));
    assert(pixels);
    FojDemo state;
    foj_demo_init(&state);
    state.cursor_x=3;
    state.cursor_y=2;
    state.selected=true;
    foj_iso_render(&state,pixels,width,height,width);
    int sx,sy;
    foj_iso_project(width,height,2,2,state.cells[2][2].elevation,
                    &sx,&sy);
    const uint32_t marker=UINT32_C(0xff6ce1f8); /* RGBA gold route dot */
    assert(pixels[(size_t)(sy-11)*width+(size_t)sx] == marker);
    foj_iso_project(width,height,3,2,state.cells[2][3].elevation,
                    &sx,&sy);
    assert(pixels[(size_t)(sy-11)*width+(size_t)sx] == marker);
    state.selected=false;
    foj_iso_render(&state,pixels,width,height,width);
    assert(pixels[(size_t)(sy-11)*width+(size_t)sx] != marker);
    free(pixels);
}

static void test_tiny_canvas_and_padded_stride(void) {
    enum { WIDTH = 48, HEIGHT = 32, STRIDE = 53 };
    uint32_t pixels[HEIGHT * STRIDE];
    for (size_t i = 0; i < (size_t)HEIGHT * STRIDE; ++i)
        pixels[i] = UINT32_C(0x12345678);
    FojDemo s;
    foj_demo_init(&s);
    foj_iso_render(&s, pixels, WIDTH, HEIGHT, STRIDE);
    for (int y = 0; y < HEIGHT; ++y) {
        for (int x = WIDTH; x < STRIDE; ++x)
            assert(pixels[y * STRIDE + x] == UINT32_C(0x12345678));
    }
    assert(pixels[0] != UINT32_C(0x12345678));

    /* Invalid stride must not touch the buffer. */
    pixels[0] = UINT32_C(0x12345678);
    foj_iso_render(&s, pixels, WIDTH, HEIGHT, WIDTH - 1);
    assert(pixels[0] == UINT32_C(0x12345678));
}

static void test_battle_health_overlay_and_result_banner(void) {
    const int width=1280, height=720;
    const size_t count=(size_t)width*(size_t)height;
    uint32_t *pixels=calloc(count,sizeof(*pixels));
    assert(pixels);
    FojBattle battle;
    foj_battle_init(&battle);

    foj_iso_render(&battle.map,pixels,width,height,width);
    uint64_t without_hud=fingerprint(pixels,count);
    foj_iso_render_battle(&battle,pixels,width,height,width);
    uint64_t healthy=fingerprint(pixels,count);
    assert(healthy!=without_hud);

    battle.hero_hp=1;
    battle.enemy_hp=3;
    foj_iso_render_battle(&battle,pixels,width,height,width);
    assert(fingerprint(pixels,count)!=healthy);

    battle.outcome=FOJ_BATTLE_WON;
    foj_iso_render_battle(&battle,pixels,width,height,width);
    assert(pixels[0]==UINT32_C(0xff7fb938)); /* generated win strip */

    battle.outcome=FOJ_BATTLE_LOST;
    foj_iso_render_battle(&battle,pixels,width,height,width);
    assert(pixels[0]==UINT32_C(0xff4a3ed2)); /* generated loss strip */
    free(pixels);
}

static void test_enemy_forecast_marker_and_attack_warning(void) {
    enum { WIDTH=1280, HEIGHT=720 };
    uint32_t *pixels=calloc((size_t)WIDTH*(size_t)HEIGHT,sizeof(*pixels));
    assert(pixels);
    FojBattle battle;
    foj_battle_init(&battle);
    FojEnemyTurnForecast projected;
    assert(foj_battle_forecast_enemy_turn(&battle,&projected));
    assert(projected.event==FOJ_BATTLE_ENEMY_MOVED);
    foj_iso_render_battle(&battle,pixels,WIDTH,HEIGHT,WIDTH);
    int sx,sy;
    const int fx=projected.enemy_x_after, fy=projected.enemy_y_after;
    foj_iso_project(WIDTH,HEIGHT,fx,fy,
                    battle.map.cells[fy][fx].elevation,&sx,&sy);
    assert(sx+5<WIDTH && sy-11>=0);
    assert(pixels[(size_t)(sy-11)*WIDTH+(size_t)(sx+5)] ==
           UINT32_C(0xff54aef8)); /* generated amber forecast ring */

    battle.map.hero_x=5; battle.map.hero_y=2;
    battle.map.enemy_x=6; battle.map.enemy_y=2;
    foj_iso_render_battle(&battle,pixels,WIDTH,HEIGHT,WIDTH);
    assert(pixels[0]==UINT32_C(0xff54aef8)); /* attack warning */
    battle.outcome=FOJ_BATTLE_WON;
    foj_iso_render_battle(&battle,pixels,WIDTH,HEIGHT,WIDTH);
    assert(pixels[0]==UINT32_C(0xff7fb938)); /* victory beats warning */
    free(pixels);
}

static void test_guard_indicator_and_cleanup_after_enemy_turn(void) {
    enum { WIDTH=1280, HEIGHT=720 };
    uint32_t *pixels=calloc((size_t)WIDTH*(size_t)HEIGHT,sizeof(*pixels));
    assert(pixels);
    FojBattle battle;
    foj_battle_init(&battle);
    int sx,sy;
    foj_iso_project(WIDTH,HEIGHT,battle.map.hero_x,battle.map.hero_y,
                    battle.map.cells[battle.map.hero_y][battle.map.hero_x].elevation,
                    &sx,&sy);
    const size_t mark=(size_t)(sy-12)*WIDTH+(size_t)(sx+24);
    foj_iso_render_battle(&battle,pixels,WIDTH,HEIGHT,WIDTH);
    const uint32_t without=pixels[mark];
    assert(foj_battle_guard(&battle)==FOJ_BATTLE_GUARDED);
    foj_iso_render_battle(&battle,pixels,WIDTH,HEIGHT,WIDTH);
    assert(pixels[mark]==UINT32_C(0xff8fd126));
    assert(pixels[mark]!=without);
    (void)foj_battle_end_turn(&battle);
    foj_iso_render_battle(&battle,pixels,WIDTH,HEIGHT,WIDTH);
    assert(pixels[mark]!=UINT32_C(0xff8fd126));
    free(pixels);
}

static void test_hero_attack_forecast_ring_and_guard_conflict(void) {
    enum { WIDTH=1280, HEIGHT=720 };
    const size_t count=(size_t)WIDTH*HEIGHT;
    uint32_t *pixels=calloc(count,sizeof(*pixels));
    assert(pixels);
    FojBattle battle;
    foj_battle_init(&battle);
    battle.map.hero_x=5; battle.map.hero_y=2;
    battle.map.enemy_x=6; battle.map.enemy_y=2;
    battle.map.cursor_x=6; battle.map.cursor_y=2;
    int sx,sy;
    foj_iso_project(WIDTH,HEIGHT,battle.map.enemy_x,battle.map.enemy_y,
                    battle.map.cells[battle.map.enemy_y][battle.map.enemy_x].elevation,
                    &sx,&sy);
    const size_t marker=(size_t)(sy-11)*WIDTH+(size_t)(sx+17);
    const FojBattle before=battle;
    foj_iso_render_battle(&battle,pixels,WIDTH,HEIGHT,WIDTH);
    assert(pixels[marker]==UINT32_C(0xff5bd6f4));
    assert(memcmp(&before,&battle,sizeof(battle))==0);
    assert(foj_battle_guard(&battle)==FOJ_BATTLE_GUARDED);
    foj_iso_render_battle(&battle,pixels,WIDTH,HEIGHT,WIDTH);
    assert(pixels[marker]!=UINT32_C(0xff5bd6f4));
    free(pixels);
}

static void test_movement_undo_marker_vanishes_after_B(void) {
    enum { WIDTH=1280, HEIGHT=720 };
    uint32_t *pixels=calloc((size_t)WIDTH*HEIGHT,sizeof(*pixels));
    assert(pixels);
    FojBattle b;
    foj_battle_init(&b);
    assert(foj_battle_confirm(&b)==FOJ_BATTLE_SELECTED);
    foj_battle_move_cursor(&b,1,0);
    assert(foj_battle_confirm(&b)==FOJ_BATTLE_MOVED);
    int px,py;
    foj_iso_project(WIDTH,HEIGHT,b.map.hero_x,b.map.hero_y,
                    b.map.cells[b.map.hero_y][b.map.hero_x].elevation,
                    &px,&py);
    foj_iso_render_battle(&b,pixels,WIDTH,HEIGHT,WIDTH);
    assert(pixels[(size_t)(py-13)*WIDTH+(size_t)(px-26)]==
           UINT32_C(0xffc9f171));
    assert(foj_battle_cancel(&b)==FOJ_BATTLE_MOVE_UNDONE);
    foj_iso_render_battle(&b,pixels,WIDTH,HEIGHT,WIDTH);
    assert(pixels[(size_t)(py-13)*WIDTH+(size_t)(px-26)]!=
           UINT32_C(0xffc9f171));
    free(pixels);
}

static void test_selected_movement_threat_markers_and_cleanup(void) {
    enum { WIDTH=1280, HEIGHT=720 };
    uint32_t *pixels=calloc((size_t)WIDTH*HEIGHT,sizeof(*pixels));
    assert(pixels);
    FojBattle battle;
    foj_battle_init(&battle);
    assert(foj_battle_confirm(&battle)==FOJ_BATTLE_SELECTED);
    const FojBattle before=battle;
    foj_iso_render_battle(&battle,pixels,WIDTH,HEIGHT,WIDTH);
    assert(memcmp(&before,&battle,sizeof(battle))==0);
    int sx,sy;
    foj_iso_project(WIDTH,HEIGHT,2,2,battle.map.cells[2][2].elevation,
                    &sx,&sy);
    const size_t safe=(size_t)(sy+11)*WIDTH+(size_t)(sx+13);
    assert(pixels[safe]==UINT32_C(0xff829e3b));
    foj_iso_project(WIDTH,HEIGHT,5,2,battle.map.cells[2][5].elevation,
                    &sx,&sy);
    const size_t atRisk=(size_t)(sy+11)*WIDTH+(size_t)(sx+9);
    const size_t secondDamage=(size_t)(sy+11)*WIDTH+(size_t)(sx+15);
    assert(pixels[atRisk]==UINT32_C(0xff508df4));
    assert(pixels[secondDamage]==UINT32_C(0xff508df4));
    assert(foj_battle_cancel(&battle)==FOJ_BATTLE_CANCELED);
    foj_iso_render_battle(&battle,pixels,WIDTH,HEIGHT,WIDTH);
    assert(pixels[safe]!=UINT32_C(0xff829e3b));
    assert(pixels[atRisk]!=UINT32_C(0xff508df4));
    free(pixels);
}

int main(void) {
    test_projection();
    test_render_and_reachable_highlights();
    test_tiny_canvas_and_padded_stride();
    test_selected_route_overlay_and_cancel();
    test_battle_health_overlay_and_result_banner();
    test_enemy_forecast_marker_and_attack_warning();
    test_guard_indicator_and_cleanup_after_enemy_turn();
    test_hero_attack_forecast_ring_and_guard_conflict();
    test_movement_undo_marker_vanishes_after_B();
    test_selected_movement_threat_markers_and_cleanup();
    puts("Synthetic isometric renderer checks passed (ten scenarios)");
    return 0;
}
