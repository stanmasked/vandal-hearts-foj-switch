/* Synthetic FoJ COLL parser tests. All fixtures generated at runtime. */
#include "coll_grid.h"
#include <assert.h>
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static const char *tiny =
    "2,2,-10,-20,10,10,\r\n"
    "0,0,0,0,0,0,false,false,\r\n"
    "1,0,1,2,3,4,true,false,\r\n"
    "0,1,-1,0,1,2,false,true,\r\n"
    "1,1,2.5,2.5,2.5,2.5,false,false,\r\n";

static void test_two_by_two(void) {
    FojCollGrid *grid = malloc(sizeof(*grid));
    assert(grid);
    assert(foj_coll_parse(tiny, strlen(tiny), grid) == FOJ_COLL_OK);
    assert(grid->width == 2 && grid->height == 2);
    assert(grid->origin[0] == -10 && grid->origin[1] == -20);
    assert(grid->step[0] == 10 && grid->step[1] == 10);
    assert(grid->samples[0][1][2] == 3);
    assert(grid->samples[1][0][0] == -1);
    assert(grid->samples[1][1][0] == 2.5f);
    assert(grid->flags[0][1][0] == 1 && grid->flags[0][1][1] == 0);
    assert(grid->flags[1][0][1] == 1);
    free(grid);
}

static void test_actual_dimension_synthetic(void) {
    /* Match FoJ's observed 50x50 grid *dimensions* without game data. */
    FojCollGrid *grid = malloc(sizeof(*grid));
    char *data = malloc(250000);
    assert(grid && data);
    size_t cursor = 0;
    cursor += (size_t)snprintf(data + cursor, 250000 - cursor,
                              "50,50,-250,-250,10,10,\n");
    for (int y = 0; y < 50; ++y)
        for (int x = 0; x < 50; ++x) {
            int added = snprintf(
                data + cursor, 250000 - cursor,
                "%d,%d,%.3f,0,0,0,%s,false,\n", x, y,
                (float)x * 0.25f + (float)y * 0.1f,
                ((x + y) % 11) == 0 ? "true" : "false"
            );
            assert(added > 0 && (size_t)added < 250000 - cursor);
            cursor += (size_t)added;
        }
    assert(foj_coll_parse(data, cursor, grid) == FOJ_COLL_OK);
    assert(grid->width * grid->height == 2500);
    assert(grid->samples[49][49][0] > 17.14f);
    assert(grid->flags[0][0][0] == 1);
    assert(grid->flags[0][1][0] == 0);
    free(data);
    free(grid);
}

static void test_errors(void) {
    FojCollGrid *grid = malloc(sizeof(*grid));
    assert(grid);
    assert(foj_coll_parse(NULL, 1, grid) == FOJ_COLL_ARGUMENT);
    assert(foj_coll_parse(tiny, 0, grid) == FOJ_COLL_LIMIT);
    assert(foj_coll_parse(tiny, FOJ_COLL_MAX_FILE_BYTES + 1, grid) == FOJ_COLL_LIMIT);
    assert(foj_coll_parse(tiny, strlen(tiny), NULL) == FOJ_COLL_ARGUMENT);
    const char *huge = "65,1,0,0,10,10,\n";
    assert(foj_coll_parse(huge, strlen(huge), grid) == FOJ_COLL_DIMENSIONS);
    const char *zero_step = "1,1,0,0,0,10,\n0,0,0,0,0,0,false,false,\n";
    assert(foj_coll_parse(zero_step, strlen(zero_step), grid) == FOJ_COLL_FORMAT);
    const char *nan_data = "1,1,0,0,10,10,\n0,0,nan,0,0,0,false,false,\n";
    assert(foj_coll_parse(nan_data, strlen(nan_data), grid) == FOJ_COLL_FORMAT);
    const char *inf_data = "1,1,0,0,10,10,\n0,0,inf,0,0,0,false,false,\n";
    assert(foj_coll_parse(inf_data, strlen(inf_data), grid) == FOJ_COLL_FORMAT);
    const char *bad_bool = "1,1,0,0,10,10,\n0,0,0,0,0,0,maybe,false,\n";
    assert(foj_coll_parse(bad_bool, strlen(bad_bool), grid) == FOJ_COLL_FORMAT);
    const char *bad_coord = "1,1,0,0,10,10,\n1,0,0,0,0,0,false,false,\n";
    assert(foj_coll_parse(bad_coord, strlen(bad_coord), grid) == FOJ_COLL_COORDINATES);
    const char *truncated = "2,1,0,0,10,10,\n0,0,0,0,0,0,false,false,\n";
    assert(foj_coll_parse(truncated, strlen(truncated), grid) == FOJ_COLL_COUNT);
    const char *extra = "1,1,0,0,10,10,\n0,0,0,0,0,0,false,false,\n0,1,0,0,0,0,false,false,\n";
    assert(foj_coll_parse(extra, strlen(extra), grid) == FOJ_COLL_COUNT);
    const char *nul = "1,1,0,0,10,10,\n0,0,0,0,0,0,false,false,\n";
    char bad[128];
    strcpy(bad, nul);
    bad[12] = '\0';
    assert(foj_coll_parse(bad, strlen(nul), grid) == FOJ_COLL_FORMAT);
    free(grid);
}

int main(void) {
    test_two_by_two();
    test_actual_dimension_synthetic();
    test_errors();
    puts("COLL grid parser: tiny, 50x50 and rejection tests passed");
    return 0;
}
