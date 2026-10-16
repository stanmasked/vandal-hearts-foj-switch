/* Original standalone COLL diagnostic view tests, no commercial game data. */
#include "coll_grid.h"
#include "coll_view.h"
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>

static uint64_t checksum(const uint32_t *pixels, size_t count) {
    uint64_t value = UINT64_C(0xcbf29ce484222325);
    for (size_t i = 0; i < count; ++i)
        value = (value ^ pixels[i]) * UINT64_C(0x100000001b3);
    return value;
}

int main(void) {
    const int width = 320, height = 240, stride = 336;
    FojCollGrid *grid = calloc(1, sizeof(*grid));
    uint32_t *pixels = malloc(sizeof(*pixels) * height * stride);
    assert(grid && pixels);
    grid->width = grid->height = 50;
    grid->step[0] = grid->step[1] = 10.0f;
    for (int y = 0; y < 50; ++y)
        for (int x = 0; x < 50; ++x) {
            grid->samples[y][x][0] = (float)(x + y);
            grid->samples[y][x][1] = (float)(x - y);
            grid->samples[y][x][2] = (float)(x * y);
            grid->samples[y][x][3] = 0;
            grid->flags[y][x][0] = (uint8_t)(x == y);
            grid->flags[y][x][1] = (uint8_t)(x == 10);
        }

    for (int i = 0; i < height * stride; ++i) pixels[i] = 0x12345678u;
    foj_coll_render(grid, pixels, width, height, stride, 25, 25, 8, 0);
    uint64_t sample0 = checksum(pixels, (size_t)height * stride);
    assert(pixels[0] != 0x12345678u);
    for (int y = 0; y < height; ++y)
        for (int x = width; x < stride; ++x)
            assert(pixels[y * stride + x] == 0x12345678u);

    foj_coll_render(grid, pixels, width, height, stride, 25, 25, 8, 1);
    assert(checksum(pixels, (size_t)height * stride) != sample0);
    foj_coll_render(grid, pixels, width, height, stride, 25, 25, 8, 4);
    assert(checksum(pixels, (size_t)height * stride) != sample0);
    foj_coll_render(grid, pixels, width, height, stride, 25, 25, 24, 5);
    assert(checksum(pixels, (size_t)height * stride) != sample0);

    pixels[0] = 0x12345678u;
    foj_coll_render(grid, pixels, width, height, width - 1, 25, 25, 12, 2);
    assert(pixels[0] == 0x12345678u);

    free(pixels);
    free(grid);
    puts("COLL diagnostic rendering tests passed");
    return 0;
}
