#include "coll_view.h"

#include <math.h>
#include <stddef.h>
#include <stdint.h>

static uint32_t rgba(unsigned r, unsigned g, unsigned b) {
    return (uint32_t)(r | (g << 8) | (b << 16) | (255u << 24));
}

static void rect(uint32_t *pixels, int w, int h, int stride,
                 int x0, int y0, int x1, int y1, uint32_t color) {
    if (x0 < 0) x0 = 0;
    if (y0 < 0) y0 = 0;
    if (x1 > w) x1 = w;
    if (y1 > h) y1 = h;
    for (int y = y0; y < y1; ++y) {
        uint32_t *row = pixels + (size_t)y * (size_t)stride;
        for (int x = x0; x < x1; ++x) row[x] = color;
    }
}

void foj_coll_render(const FojCollGrid *grid, uint32_t *pixels, int width,
                     int height, int stride, int cursor_x, int cursor_y,
                     int tile_size, int channel) {
    if (!grid || !pixels || width <= 0 || height <= 0 || stride < width ||
        grid->width < 1 || grid->height < 1 ||
        grid->width > FOJ_COLL_MAX_SIDE || grid->height > FOJ_COLL_MAX_SIDE ||
        cursor_x < 0 || cursor_x >= grid->width ||
        cursor_y < 0 || cursor_y >= grid->height ||
        tile_size < 2 || tile_size > 64 || channel < 0 || channel > 5) return;

    rect(pixels, width, height, stride, 0, 0, width, height, rgba(17, 22, 34));
    float minv = 0.0f, maxv = 1.0f;
    if (channel < 4) {
        minv = INFINITY;
        maxv = -INFINITY;
        for (int y = 0; y < grid->height; ++y) {
            for (int x = 0; x < grid->width; ++x) {
                const float value = grid->samples[y][x][channel];
                if (!isfinite(value)) return;
                if (value < minv) minv = value;
                if (value > maxv) maxv = value;
            }
        }
    }

    int full_w = grid->width * tile_size, full_h = grid->height * tile_size;
    int left = full_w <= width ?
               (width - full_w) / 2 :
               width / 2 - (cursor_x * tile_size + tile_size / 2);
    int top = full_h <= height ?
              (height - full_h) / 2 :
              height / 2 - (cursor_y * tile_size + tile_size / 2);
    float range = maxv - minv;
    if (!(range > 0.0f)) range = 1.0f;

    for (int y = 0; y < grid->height; ++y) {
        for (int x = 0; x < grid->width; ++x) {
            int px = left + x * tile_size;
            int py = top + y * tile_size;
            if (px >= width || py >= height ||
                px + tile_size <= 0 || py + tile_size <= 0) continue;
            uint32_t fill;
            if (channel < 4) {
                float t = (grid->samples[y][x][channel] - minv) / range;
                if (t < 0.0f) t = 0.0f;
                if (t > 1.0f) t = 1.0f;
                /* Blue -> teal -> warm yellow = raw numeric sample visualization. */
                unsigned r = (unsigned)(30.0f + t * 200.0f);
                unsigned g = (unsigned)(62.0f + t * 130.0f);
                unsigned b = (unsigned)(160.0f - t * 115.0f);
                fill = rgba(r, g, b);
            } else {
                const unsigned flag = grid->flags[y][x][channel - 4];
                fill = flag ? rgba(218, 91, 108) : rgba(46, 66, 79);
            }
            rect(pixels, width, height, stride,
                 px + 1, py + 1, px + tile_size, py + tile_size, fill);
            if (x == cursor_x && y == cursor_y) {
                uint32_t edge = rgba(255, 232, 140);
                rect(pixels, width, height, stride, px, py, px + tile_size, py + 2, edge);
                rect(pixels, width, height, stride, px, py + tile_size - 2,
                     px + tile_size, py + tile_size, edge);
                rect(pixels, width, height, stride, px, py, px + 2, py + tile_size, edge);
                rect(pixels, width, height, stride, px + tile_size - 2, py,
                     px + tile_size, py + tile_size, edge);
            }
        }
    }
    /* Channel indicator in top-left. Not the original in-game HUD. */
    for (int i = 0; i < 6; ++i) {
        uint32_t dot = i == channel ? rgba(248, 217, 117) : rgba(78, 91, 115);
        rect(pixels, width, height, stride, 18 + i * 24, 18, 34 + i * 24, 31, dot);
    }
}
