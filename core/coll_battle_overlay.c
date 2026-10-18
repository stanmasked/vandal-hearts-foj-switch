#include "coll_battle_overlay.h"

#include <math.h>
#include <stddef.h>

enum {
    CELL_STEP = 22, CELL_DRAW = 20, PANEL_PAD = 9,
    PANEL_WIDTH = FOJ_WIDTH * CELL_STEP + PANEL_PAD * 2,
    PANEL_HEIGHT = FOJ_HEIGHT * CELL_STEP + 42,
    PANEL_TOP = 16, PANEL_RIGHT = 16,
    GRID_TOP = 33
};

static uint32_t rgba(unsigned r, unsigned g, unsigned b) {
    return r | (g << 8u) | (b << 16u) | UINT32_C(0xff000000);
}

static void paint_rect(uint32_t *pixels, int stride, int left, int top,
                       int width, int height, uint32_t color) {
    for (int y = 0; y < height; ++y) {
        uint32_t *row = pixels + (size_t)(top+y)*(size_t)stride + (size_t)left;
        for (int x = 0; x < width; ++x) row[x] = color;
    }
}

bool foj_coll_battle_overlay(const FojCollBattleWindow *window,
                              uint32_t *pixels, int width, int height,
                              int stride_pixels, int cursor_x, int cursor_y,
                              unsigned channel) {
    if (!window || !pixels || width < PANEL_WIDTH+PANEL_RIGHT ||
        height < PANEL_TOP+PANEL_HEIGHT || stride_pixels < width ||
        channel >= 6 || !foj_in_bounds(cursor_x,cursor_y) ||
        window->source_width < FOJ_WIDTH ||
        window->source_height < FOJ_HEIGHT) return false;

    float minimum=0.0f, maximum=0.0f;
    if (channel < 4) {
        minimum = maximum = window->raw[0][0][channel];
        if (!isfinite(minimum)) return false;
        for (int y=0;y<FOJ_HEIGHT;++y)
            for (int x=0;x<FOJ_WIDTH;++x) {
                const float v = window->raw[y][x][channel];
                if (!isfinite(v)) return false;
                if (v < minimum) minimum=v;
                if (v > maximum) maximum=v;
            }
    } else {
        for (int y=0;y<FOJ_HEIGHT;++y)
            for (int x=0;x<FOJ_WIDTH;++x)
                if (window->flags[y][x][channel-4u] > 1) return false;
    }

    const int x0=width-PANEL_RIGHT-PANEL_WIDTH;
    const int y0=PANEL_TOP;
    paint_rect(pixels,stride_pixels,x0,y0,PANEL_WIDTH,PANEL_HEIGHT,
               rgba(14,23,34));

    /* Six neutral channel tabs. Highlight only the selected raw channel. */
    for (unsigned tab=0;tab<6;++tab)
        paint_rect(pixels,stride_pixels,x0+9+(int)tab*28,y0+10,24,7,
                   tab==channel ? rgba(239,195,98) : rgba(65,84,95));

    const float span=maximum-minimum;
    for (int y=0;y<FOJ_HEIGHT;++y) {
        for (int x=0;x<FOJ_WIDTH;++x) {
            uint32_t color;
            if (channel >= 4) {
                color=window->flags[y][x][channel-4u] ?
                    rgba(40,177,133) : rgba(61,65,77);
            } else {
                float t=0.5f;
                if (isfinite(span) && span>0.0f) {
                    t=(window->raw[y][x][channel]-minimum)/span;
                    if (!isfinite(t)) t=0.5f;
                    if (t<0.0f) t=0.0f;
                    if (t>1.0f) t=1.0f;
                }
                unsigned intensity=(unsigned)(t*150.0f);
                color=rgba(42,56+intensity,79+intensity/2u);
            }
            const int px=x0+PANEL_PAD+x*CELL_STEP;
            const int py=y0+GRID_TOP+y*CELL_STEP;
            paint_rect(pixels,stride_pixels,px,py,CELL_DRAW,CELL_DRAW,color);
            if (x==cursor_x && y==cursor_y) {
                const uint32_t outline=rgba(255,226,120);
                paint_rect(pixels,stride_pixels,px,py,CELL_DRAW,2,outline);
                paint_rect(pixels,stride_pixels,px,py+CELL_DRAW-2,
                           CELL_DRAW,2,outline);
                paint_rect(pixels,stride_pixels,px,py,2,CELL_DRAW,outline);
                paint_rect(pixels,stride_pixels,px+CELL_DRAW-2,py,
                           2,CELL_DRAW,outline);
            }
        }
    }
    return true;
}
