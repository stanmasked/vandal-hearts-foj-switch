/*
 * Stage221: generated-only host rendering of the actual isometric battle
 * and raw COLL observation panel. No PS3 files, textures or game data.
 */
#include "coll_battle_overlay.h"
#include "isometric_demo.h"
#include "tactical_battle.h"

#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

enum { WIDTH = 1280, HEIGHT = 720 };

static void generated_raw_window(FojCollBattleWindow *window) {
    memset(window, 0, sizeof(*window));
    window->source_width=50;
    window->source_height=50;
    window->source_x=21;
    window->source_y=22;
    for (int y=0;y<FOJ_HEIGHT;++y) {
        for (int x=0;x<FOJ_WIDTH;++x) {
            for (unsigned c=0;c<4;++c)
                window->raw[y][x][c]=(float)(x*3+y*5+(int)c*7);
            window->flags[y][x][0]=(uint8_t)((x+y)%3==0);
            window->flags[y][x][1]=(uint8_t)((x*3+y)%4==0);
        }
    }
}

int main(int argc, char **argv) {
    if (argc!=2) {
        fputs("Usage: generated-coll-battle-preview OUTPUT.ppm\n",stderr);
        return 2;
    }
    const size_t pixels_count=(size_t)WIDTH*HEIGHT;
    uint32_t *pixels=calloc(pixels_count,sizeof(*pixels));
    if (!pixels) return 3;

    FojBattle battle;
    foj_battle_init(&battle);
    battle.map.cursor_x=4;
    battle.map.cursor_y=3;
    foj_iso_render_battle(&battle,pixels,WIDTH,HEIGHT,WIDTH);

    FojCollBattleWindow window;
    generated_raw_window(&window);
    if (!foj_coll_battle_overlay(&window,pixels,WIDTH,HEIGHT,WIDTH,
                                 battle.map.cursor_x,battle.map.cursor_y,0)) {
        free(pixels);
        return 4;
    }

    FILE *output=fopen(argv[1],"wb");
    if (!output) { free(pixels); return 5; }
    int okay=fprintf(output,"P6\n%d %d\n255\n",WIDTH,HEIGHT)>0;
    for (size_t i=0;i<pixels_count && okay;++i) {
        const uint32_t p=pixels[i];
        const unsigned char rgb[3]={
            (unsigned char)(p&255u),
            (unsigned char)((p>>8u)&255u),
            (unsigned char)((p>>16u)&255u)
        };
        okay=fwrite(rgb,1,sizeof(rgb),output)==sizeof(rgb);
    }
    if (fclose(output)!=0)okay=0;
    free(pixels);
    return okay?0:6;
}
