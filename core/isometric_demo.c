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

void foj_iso_render_battle_profiled(const FojBattle *battle,
                                    uint32_t *pixels,
                                    int width, int height,
                                    int stride_pixels,
                                    bool show_threat_preview,
                                    FojBattleThreatCache *cache,
                                    FojIsoPhaseClockNs clock_ns,
                                    void *clock_context,
                                    FojIsoPhaseReceipt *receipt) {
    if (receipt) {
        *receipt = (FojIsoPhaseReceipt){0};
    }
    if (!battle || !pixels || width <= 0 || height <= 0 ||
        stride_pixels < width) return;
    const uint64_t t0 = clock_ns && receipt ? clock_ns(clock_context) : 0;
    FojDemo visual = battle->map;
    if (battle->enemy_hp == 0) {
        /* Hide the defeated synthetic enemy token on the final screen. */
        visual.enemy_x = -1;
        visual.enemy_y = -1;
    }
    foj_iso_render(&visual, pixels, width, height, stride_pixels);
    const uint64_t t1 = clock_ns && receipt ? clock_ns(clock_context) : 0;
    Canvas canvas = {pixels, width, height, stride_pixels};
    int x, y;
    /* Destination danger is advisory and exists only during A movement
     * selection. Resolve the exact same enemy Y action on temporary
     * copies for each reachable cell; retain no PS3 terrain semantics. */
    FojBattleThreatPreview danger;
    const bool have_danger = show_threat_preview &&
        foj_battle_preview_movement_threat_cached(cache,battle,&danger);
    const uint64_t t2 = clock_ns && receipt ? clock_ns(clock_context) : 0;
    if (have_danger) {
        for (int dy=0;dy<FOJ_HEIGHT;++dy) {
            for (int dx=0;dx<FOJ_WIDTH;++dx) {
                if (!danger.can_move[dy][dx]) continue;
                foj_iso_project(width,height,dx,dy,
                                battle->map.cells[dy][dx].elevation,&x,&y);
                const int incoming=danger.incoming_damage[dy][dx];
                if (incoming==0) {
                    for (int yy=0;yy<4;++yy)
                        for (int xx=0;xx<6;++xx)
                            pixel(&canvas,x+11+xx,y+10+yy,
                                  rgb(59,158,130));
                } else {
                    const int bars=incoming>4 ? 4 : incoming;
                    for (int bar=0;bar<bars;++bar)
                        for (int yy=0;yy<4;++yy)
                            for (int xx=0;xx<4;++xx)
                                pixel(&canvas,x+8+bar*6+xx,y+10+yy,
                                      rgb(244,141,80));
                }
            }
        }
        /* Cursor-targeted enemy destination marker. Coordinates come
         * from the SAME simulated Y turn as risk ticks; no second AI.
         * Purple 6x6 tab is intentionally above the destination so
         * danger/guard/hp HUD and NeXium palette tests stay separate. */
        const int cx=battle->map.cursor_x, cy=battle->map.cursor_y;
        if (foj_in_bounds(cx,cy) && danger.can_move[cy][cx]) {
            const int ex=danger.enemy_x_after[cy][cx];
            const int ey=danger.enemy_y_after[cy][cx];
            if (foj_in_bounds(ex,ey)) {
                foj_iso_project(width,height,ex,ey,
                                battle->map.cells[ey][ex].elevation,&x,&y);
                for (int py=-32;py<=-27;++py)
                    for (int px=20;px<=25;++px)
                        pixel(&canvas,x+px,y+py,rgb(185,127,236));
            }
        }
    }
    const uint64_t t3 = clock_ns && receipt ? clock_ns(clock_context) : 0;
    if (foj_in_bounds(battle->map.hero_x, battle->map.hero_y)) {
        foj_iso_project(width, height, battle->map.hero_x, battle->map.hero_y,
            battle->map.cells[battle->map.hero_y][battle->map.hero_x].elevation,
            &x, &y);
        hp_bar(&canvas, x, y, battle->hero_hp, FOJ_BATTLE_HERO_MAX_HP,
               rgb(95, 193, 244));
    }
    if (battle->enemy_hp > 0 &&
        foj_in_bounds(battle->map.enemy_x, battle->map.enemy_y)) {
        foj_iso_project(width, height, battle->map.enemy_x, battle->map.enemy_y,
            battle->map.cells[battle->map.enemy_y][battle->map.enemy_x].elevation,
            &x, &y);
        hp_bar(&canvas, x, y, battle->enemy_hp, FOJ_BATTLE_ENEMY_MAX_HP,
               rgb(227, 82, 93));
    }
    /* Mint arrow mark: B can still undo this uncommitted hero move. */
    if (battle->moved_this_turn && !battle->attacked_this_turn &&
        battle->outcome == FOJ_BATTLE_ONGOING &&
        foj_in_bounds(battle->map.hero_x, battle->map.hero_y)) {
        const int hx=battle->map.hero_x, hy=battle->map.hero_y;
        foj_iso_project(width,height,hx,hy,
                        battle->map.cells[hy][hx].elevation,&x,&y);
        for (int dx=-29;dx<=-22;++dx)
            for (int dy=-16;dy<=-10;++dy)
                pixel(&canvas,x+dx,y+dy,rgb(113,241,201));
    }
    if (battle->guarded_this_turn &&
        battle->outcome == FOJ_BATTLE_ONGOING &&
        foj_in_bounds(battle->map.hero_x, battle->map.hero_y)) {
        const int hx=battle->map.hero_x, hy=battle->map.hero_y;
        foj_iso_project(width, height, hx, hy,
                        battle->map.cells[hy][hx].elevation, &x, &y);
        /* Bright mint marker beside the hero: guarding is active until Y. */
        for (int py=-15;py<=-9;++py)
            for (int px=21;px<=27;++px)
                pixel(&canvas,x+px,y+py,rgb(38,209,143));
    }
    /* Preview the hero's X attack only when the real attack is legal.
     * Gold outline = current target; gold bar below current red HP =
     * enemy HP after the speculative hit. This does not commit damage. */
    FojHeroAttackForecast attack_view;
    if (foj_battle_forecast_attack(battle, &attack_view) &&
        foj_in_bounds(battle->map.enemy_x, battle->map.enemy_y)) {
        const int ax=battle->map.enemy_x, ay=battle->map.enemy_y;
        foj_iso_project(width,height,ax,ay,
                        battle->map.cells[ay][ax].elevation,&x,&y);
        const uint32_t outline=rgb(244,214,91);
        for (int dy=-17;dy<=17;++dy)
            for (int dx=-17;dx<=17;++dx) {
                const int radius2=dx*dx+dy*dy;
                if (radius2>=225 && radius2<=289)
                    pixel(&canvas,x+dx,y-11+dy,outline);
            }
        hp_bar(&canvas,x,y+8,attack_view.enemy_hp_after,
               FOJ_BATTLE_ENEMY_MAX_HP,rgb(244,214,91));
    }
    /* A small amber ring marks the enemy's NEXT cell, not its current
     * position, and never changes tactical state or movement legality. */
    FojEnemyTurnForecast forecast;
    if (foj_battle_forecast_enemy_turn(battle, &forecast)) {
        if (forecast.event == FOJ_BATTLE_ENEMY_MOVED &&
            foj_in_bounds(forecast.enemy_x_after, forecast.enemy_y_after)) {
            const int fx=forecast.enemy_x_after;
            const int fy=forecast.enemy_y_after;
            foj_iso_project(width, height, fx, fy,
                            battle->map.cells[fy][fx].elevation, &x, &y);
            disk(&canvas, x, y-11, 6, rgb(248, 174, 84));
            disk(&canvas, x, y-11, 3, rgb(36, 47, 55));
        }
        if (forecast.event == FOJ_BATTLE_ENEMY_ATTACKED ||
            forecast.event == FOJ_BATTLE_DEFEAT) {
            /* Thin warning strip means ending the turn would hurt hero. */
            for (int y0=0;y0<4 && y0<height;++y0)
                for (int x0=0;x0<width;++x0)
                    pixel(&canvas,x0,y0,rgb(248,174,84));
        }
    }
    if (battle->outcome != FOJ_BATTLE_ONGOING) {
        const uint32_t color = battle->outcome == FOJ_BATTLE_WON ?
            rgb(56, 185, 127) : rgb(210, 62, 74);
        for (int y0 = 0; y0 < 8 && y0 < height; ++y0)
            for (int x0 = 0; x0 < width; ++x0)
                pixel(&canvas, x0, y0, color);
    }
    if (receipt && clock_ns) {
        const uint64_t t4 = clock_ns(clock_context);
        receipt->forecast_available = have_danger;
        if (t0 < t1 && t1 < t2 && t2 < t3 && t3 < t4) {
            receipt->terrain_ns = t1 - t0;
            receipt->threat_compute_ns = t2 - t1;
            receipt->threat_paint_ns = t3 - t2;
            receipt->battle_hud_ns = t4 - t3;
            receipt->whole_raster_ns = t4 - t0;
            receipt->valid = true;
        }
    }
}

/* Production function: no clock reads, no HUD receipts, same exact drawing.
 * The same helper is used by the opt-in Stage246 guest build. */
void foj_iso_render_battle_cached_options(const FojBattle *battle,
                                          uint32_t *pixels,
                                          int width, int height,
                                          int stride_pixels,
                                          bool show_threat_preview,
                                          FojBattleThreatCache *cache) {
    foj_iso_render_battle_profiled(battle,pixels,width,height,stride_pixels,
                                    show_threat_preview,cache,NULL,NULL,NULL);
}

/* Preserve all established entry points and framebuffer contracts. */
void foj_iso_render_battle_options(const FojBattle *battle, uint32_t *pixels,
                                   int width, int height, int stride_pixels,
                                   bool show_threat_preview) {
    foj_iso_render_battle_cached_options(battle,pixels,width,height,
                                         stride_pixels,show_threat_preview,NULL);
}

/* Keep the original signature and defaults for all existing game code. */
void foj_iso_render_battle(const FojBattle *battle, uint32_t *pixels,
                           int width, int height, int stride_pixels) {
    foj_iso_render_battle_options(battle,pixels,width,height,stride_pixels,true);
}
