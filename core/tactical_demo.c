#include "tactical_demo.h"

#include <string.h>

/* Fully invented terrain. No FoJ game assets or gameplay data. */
void foj_demo_init(FojDemo *state) {
    memset(state, 0, sizeof(*state));
    state->hero_x = 1;
    state->hero_y = 2;
    state->enemy_x = 6;
    state->enemy_y = 3;
    state->cursor_x = state->hero_x;
    state->cursor_y = state->hero_y;

    /* A height-two plateau with two height-one ramps. */
    for (int y = 1; y <= 3; ++y) {
        for (int x = 3; x <= 4; ++x) {
            state->cells[y][x].elevation = 2;
        }
    }
    state->cells[2][2].elevation = 1;
    state->cells[2][5].elevation = 1;
    state->cells[1][2].blocked = true;
    state->cells[3][2].blocked = true;
}

bool foj_in_bounds(int x, int y) {
    return x >= 0 && y >= 0 && x < FOJ_WIDTH && y < FOJ_HEIGHT;
}

void foj_move_cursor(FojDemo *state, int dx, int dy) {
    int x = state->cursor_x + dx;
    int y = state->cursor_y + dy;
    if (x < 0) x = 0;
    if (x >= FOJ_WIDTH) x = FOJ_WIDTH - 1;
    if (y < 0) y = 0;
    if (y >= FOJ_HEIGHT) y = FOJ_HEIGHT - 1;
    state->cursor_x = x;
    state->cursor_y = y;
}

void foj_reachability(const FojDemo *state,
                      uint8_t distances[FOJ_HEIGHT][FOJ_WIDTH]) {
    for (int y = 0; y < FOJ_HEIGHT; ++y) {
        for (int x = 0; x < FOJ_WIDTH; ++x) {
            distances[y][x] = FOJ_UNREACHABLE;
        }
    }
    if (!foj_in_bounds(state->hero_x, state->hero_y)) return;

    int queue_x[FOJ_TILE_COUNT], queue_y[FOJ_TILE_COUNT];
    int front = 0, back = 0;
    distances[state->hero_y][state->hero_x] = 0;
    queue_x[back] = state->hero_x;
    queue_y[back++] = state->hero_y;

    static const int dx[] = {0, 1, 0, -1};
    static const int dy[] = {-1, 0, 1, 0};

    while (front < back) {
        const int x = queue_x[front];
        const int y = queue_y[front++];
        const uint8_t cost = distances[y][x];
        if (cost >= FOJ_MOVE_BUDGET) continue;

        for (int d = 0; d < 4; ++d) {
            const int nx = x + dx[d], ny = y + dy[d];
            if (!foj_in_bounds(nx, ny)) continue;
            if (distances[ny][nx] != FOJ_UNREACHABLE) continue;
            if (state->cells[ny][nx].blocked) continue;
            if (nx == state->enemy_x && ny == state->enemy_y) continue;

            const int delta = (int)state->cells[ny][nx].elevation -
                              (int)state->cells[y][x].elevation;
            if (delta > FOJ_MAX_STEP_HEIGHT ||
                delta < -FOJ_MAX_STEP_HEIGHT) continue;

            distances[ny][nx] = (uint8_t)(cost + 1);
            /* Each tile enters the FIFO queue at most once. */
            queue_x[back] = nx;
            queue_y[back++] = ny;
        }
    }
}

FojAction foj_press_a(FojDemo *state) {
    if (!state->selected) {
        if (state->cursor_x == state->hero_x &&
            state->cursor_y == state->hero_y) {
            state->selected = true;
            return FOJ_ACTION_SELECTED;
        }
        return FOJ_ACTION_NONE;
    }

    uint8_t distances[FOJ_HEIGHT][FOJ_WIDTH];
    foj_reachability(state, distances);
    const int x = state->cursor_x, y = state->cursor_y;
    if (!foj_in_bounds(x, y) ||
        (x == state->hero_x && y == state->hero_y) ||
        distances[y][x] == FOJ_UNREACHABLE) {
        return FOJ_ACTION_REJECTED;
    }
    state->hero_x = x;
    state->hero_y = y;
    state->selected = false;
    return FOJ_ACTION_MOVED;
}

FojAction foj_press_b(FojDemo *state) {
    if (!state->selected) return FOJ_ACTION_NONE;
    state->selected = false;
    return FOJ_ACTION_CANCELED;
}
