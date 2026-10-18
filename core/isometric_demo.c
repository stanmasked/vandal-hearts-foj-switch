#include "isometric_demo.h"

#include <stddef.h>
#include <stdint.h>

enum { HALF_W = 47, HALF_H = 23, STEP_X = 54, STEP_Y = 30, STEP_Z = 18 };
typedef struct { int x, y; } Point;
typedef struct { uint32_t *data; int width, height, stride; } Canvas;

static uint32_t rgb(unsigned r, unsigned g, unsigned b) {
    /* libnx PIXEL_FORMAT_RGBA_8888: R in least-significant byte. */
    return (uint32_t)(r | (g << 8) | (b << 16) | (255u << 24));
}

static void pixel(Canvas *c, int x, int y, uint32_t color) {
    if (x >= 0 && y >= 0 && x < c->width && y < c->height)
        c->data[(size_t)y * (size_t)c->stride + (size_t)x] = color;
}

static int min2(int a, int b) { return a < b ? a : b; }
static int max2(int a, int b) { return a > b ? a : b; }

static int64_t cross(Point a, Point b, Point p) {
    return (int64_t)(b.x - a.x) * (p.y - a.y) -
           (int64_t)(b.y - a.y) * (p.x - a.x);
}

static void triangle(Canvas *canvas, Point a, Point b, Point d, uint32_t color) {
    int xmin = max2(0, min2(a.x, min2(b.x, d.x)));
    int xmax = min2(canvas->width - 1, max2(a.x, max2(b.x, d.x)));
    int ymin = max2(0, min2(a.y, min2(b.y, d.y)));
    int ymax = min2(canvas->height - 1, max2(a.y, max2(b.y, d.y)));
    for (int y = ymin; y <= ymax; ++y) {
        for (int x = xmin; x <= xmax; ++x) {
            Point p = {x, y};
            const int64_t ab = cross(a, b, p);
            const int64_t bd = cross(b, d, p);
            const int64_t da = cross(d, a, p);
            if ((ab >= 0 && bd >= 0 && da >= 0) ||
                (ab <= 0 && bd <= 0 && da <= 0)) {
                pixel(canvas, x, y, color);
            }
        }
    }
}

static void quad(Canvas *c, Point a, Point b, Point d, Point e,
                 uint32_t color) {
    triangle(c, a, b, d, color);
    triangle(c, a, d, e, color);
}

static void line(Canvas *c, Point a, Point b, uint32_t color) {
    int dx = a.x > b.x ? a.x - b.x : b.x - a.x;
    int dy = a.y > b.y ? a.y - b.y : b.y - a.y;
    int sx = a.x < b.x ? 1 : -1;
    int sy = a.y < b.y ? 1 : -1;
    int err = dx - dy;
    for (;;) {
        pixel(c, a.x, a.y, color);
        if (a.x == b.x && a.y == b.y) break;
        int twice = 2 * err;
        if (twice > -dy) { err -= dy; a.x += sx; }
        if (twice < dx) { err += dx; a.y += sy; }
    }
}

static void disk(Canvas *c, int x, int y, int radius, uint32_t color) {
    for (int dy = -radius; dy <= radius; ++dy) {
        for (int dx = -radius; dx <= radius; ++dx) {
            if (dx * dx + dy * dy <= radius * radius)
                pixel(c, x + dx, y + dy, color);
        }
    }
}

void foj_iso_project(int width, int height, int x, int y, int elevation,
                     int *screen_x, int *screen_y) {
    *screen_x = width / 2 + (x - y) * STEP_X;
    *screen_y = height / 6 + (x + y) * STEP_Y - elevation * STEP_Z;
}

void foj_iso_render(const FojDemo *state, uint32_t *pixels,
                    int width, int height, int stride_pixels) {
    if (!state || !pixels || width <= 0 || height <= 0 ||
        stride_pixels < width) return;
    Canvas c = {pixels, width, height, stride_pixels};

    const uint32_t background = rgb(13, 19, 33);
    for (int y = 0; y < height; ++y) {
        uint32_t *row = pixels + (size_t)y * (size_t)stride_pixels;
        for (int x = 0; x < width; ++x) row[x] = background;
    }

    uint8_t distance[FOJ_HEIGHT][FOJ_WIDTH];
    foj_reachability(state, distance);
    /* Back-to-front by increasing x+y depth. Correct for this small test
       terrain; not a general-purpose 3D visibility / occlusion renderer. */
    for (int diagonal = 0; diagonal < FOJ_WIDTH + FOJ_HEIGHT - 1; ++diagonal) {
        for (int y = 0; y < FOJ_HEIGHT; ++y) {
            int x = diagonal - y;
            if (!foj_in_bounds(x, y)) continue;
            const FojCell cell = state->cells[y][x];
            int cx, cy;
            foj_iso_project(width, height, x, y, cell.elevation, &cx, &cy);
            Point top = {cx, cy - HALF_H};
            Point right = {cx + HALF_W, cy};
            Point bottom = {cx, cy + HALF_H};
            Point left = {cx - HALF_W, cy};
            int depth = cell.elevation * STEP_Z;
            Point right_down = {right.x, right.y + depth};
            Point bottom_down = {bottom.x, bottom.y + depth};
            Point left_down = {left.x, left.y + depth};

            quad(&c, left, bottom, bottom_down, left_down, rgb(35, 49, 58));
            quad(&c, bottom, right, right_down, bottom_down, rgb(45, 61, 67));

            uint32_t top_color = ((x + y) & 1) ?
                rgb(75, 98, 91) : rgb(84, 107, 99);
            if (cell.blocked) top_color = rgb(83, 65, 65);
            if (state->selected && distance[y][x] != FOJ_UNREACHABLE &&
                !(x == state->hero_x && y == state->hero_y))
                top_color = rgb(55, 132, 123);
            triangle(&c, top, right, bottom, top_color);
            triangle(&c, top, bottom, left, top_color);
            const uint32_t edge = rgb(25, 38, 47);
            line(&c, top, right, edge);
            line(&c, right, bottom, edge);
            line(&c, bottom, left, edge);
            line(&c, left, top, edge);

            if (x == state->hero_x && y == state->hero_y) {
                disk(&c, cx, cy - 11, 14, rgb(20, 39, 50));
                disk(&c, cx, cy - 11, 10, rgb(95, 193, 244));
            }
            if (x == state->enemy_x && y == state->enemy_y) {
                disk(&c, cx, cy - 11, 14, rgb(49, 19, 29));
                disk(&c, cx, cy - 11, 10, rgb(227, 82, 93));
            }
            if (x == state->cursor_x && y == state->cursor_y) {
                const uint32_t highlight = rgb(255, 216, 85);
                line(&c, top, right, highlight);
                line(&c, right, bottom, highlight);
                line(&c, bottom, left, highlight);
                line(&c, left, top, highlight);
            }
        }
    }

    /* Final overlay so subsequent terrain faces cannot hide the route.
     * This is a synthetic *preview*: moving still requires pressing A.
     * Only intermediate/destination cells get markers; the hero is
     * already visible as a blue token. */
    if (state->selected) {
        FojRoute route;
        if (foj_demo_preview_route(state,state->cursor_x,state->cursor_y,
                                   &route)) {
            for (unsigned step=1u;step<route.count;++step) {
                const int x=route.x[step],y=route.y[step];
                int sx,sy;
                foj_iso_project(width,height,x,y,
                                state->cells[y][x].elevation,&sx,&sy);
                disk(&c,sx,sy-11,6,rgb(36,47,55));
                disk(&c,sx,sy-11,4,rgb(248,225,108));
            }
        }
    }
}

/* The overlay is deliberately primitive and uses only generated geometry.
 * Its health bars are readable without a font, textures, or PS3 assets. */
static void hp_bar(Canvas *canvas, int cx, int cy, unsigned hp,
                   unsigned maximum, uint32_t color) {
    if (hp > maximum) hp = maximum;
    const int left = cx - 21;
    const int top = cy - 47;
    const int filled = (int)((hp * 40u) / maximum);
    for (int y = 0; y < 7; ++y) {
        for (int x = 0; x < 42; ++x) {
            uint32_t shade = rgb(15, 22, 29);
            if (y >= 1 && y <= 5 && x >= 1 && x <= filled)
                shade = color;
            pixel(canvas, left + x, top + y, shade);
        }
    }
}

void foj_iso_render_battle(const FojBattle *battle, uint32_t *pixels,
                           int width, int height, int stride_pixels) {
    if (!battle || !pixels || width <= 0 || height <= 0 ||
        stride_pixels < width) return;
    foj_iso_render(&battle->map, pixels, width, height, stride_pixels);
    Canvas canvas = {pixels, width, height, stride_pixels};
    int x, y;
    if (foj_in_bounds(battle->map.hero_x, battle->map.hero_y)) {
        foj_iso_project(width, height, battle->map.hero_x, battle->map.hero_y,
            battle->map.cells[battle->map.hero_y][battle->map.hero_x].elevation,
            &x, &y);
        hp_bar(&canvas, x, y, battle->hero_hp, FOJ_BATTLE_HERO_MAX_HP,
               rgb(95, 193, 244));
    }
    if (foj_in_bounds(battle->map.enemy_x, battle->map.enemy_y)) {
        foj_iso_project(width, height, battle->map.enemy_x, battle->map.enemy_y,
            battle->map.cells[battle->map.enemy_y][battle->map.enemy_x].elevation,
            &x, &y);
        hp_bar(&canvas, x, y, battle->enemy_hp, FOJ_BATTLE_ENEMY_MAX_HP,
               rgb(227, 82, 93));
    }
    if (battle->outcome != FOJ_BATTLE_ONGOING) {
        const uint32_t color = battle->outcome == FOJ_BATTLE_WON ?
            rgb(56, 185, 127) : rgb(210, 62, 74);
        for (int y0 = 0; y0 < 8 && y0 < height; ++y0)
            for (int x0 = 0; x0 < width; ++x0)
                pixel(&canvas, x0, y0, color);
    }
}
