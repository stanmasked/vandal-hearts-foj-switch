#ifndef FOJ_TACTICAL_DEMO_H
#define FOJ_TACTICAL_DEMO_H

/*
 * Original synthetic tactical-logic research, NOT Flames of Judgment code.
 * Platform-independent, fixed-size structures; no dynamic allocations.
 */
#include <stdbool.h>
#include <stdint.h>

enum {
    FOJ_WIDTH = 8,
    FOJ_HEIGHT = 6,
    FOJ_TILE_COUNT = FOJ_WIDTH * FOJ_HEIGHT,
    FOJ_MOVE_BUDGET = 4,
    FOJ_MAX_STEP_HEIGHT = 1,
    FOJ_UNREACHABLE = 255,
    FOJ_ROUTE_MAX_CELLS = FOJ_MOVE_BUDGET + 1
};

typedef struct {
    uint8_t elevation;
    bool blocked;
} FojCell;

typedef struct {
    FojCell cells[FOJ_HEIGHT][FOJ_WIDTH];
    int hero_x, hero_y;
    int enemy_x, enemy_y;
    int cursor_x, cursor_y;
    bool selected;
} FojDemo;

typedef enum {
    FOJ_ACTION_NONE = 0,
    FOJ_ACTION_SELECTED,
    FOJ_ACTION_MOVED,
    FOJ_ACTION_REJECTED,
    FOJ_ACTION_CANCELED
} FojAction;

/* Deterministic, bounded local route preview for INVENTED test terrain.
 * Route includes both the current hero tile and the target destination.
 * A zero count means no legal movement path. This is not FoJ pathfinding. */
typedef struct {
    uint8_t count;
    uint8_t x[FOJ_ROUTE_MAX_CELLS];
    uint8_t y[FOJ_ROUTE_MAX_CELLS];
} FojRoute;

bool foj_demo_preview_route(const FojDemo *state, int target_x, int target_y,
                            FojRoute *route);
void foj_demo_init(FojDemo *state);
bool foj_in_bounds(int x, int y);
void foj_move_cursor(FojDemo *state, int dx, int dy);
void foj_reachability(const FojDemo *state,
                      uint8_t distances[FOJ_HEIGHT][FOJ_WIDTH]);
FojAction foj_press_a(FojDemo *state);
FojAction foj_press_b(FojDemo *state);

#endif
