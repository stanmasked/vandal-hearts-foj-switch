/* Command-line C validation of a *locally supplied* COLL grid.
 * Only aggregate geometry/flag stats are printed. No file contents exported.
 */
#include "coll_grid.h"
#include <math.h>
#include <stdio.h>
#include <stdlib.h>

int main(int argc, char **argv) {
    if (argc == 2 && argv[1][0] == '-' && argv[1][1] == '-') {
        puts("Usage: foj-coll-validate PATH_TO_LOCAL_MAP.coll");
        return 0;
    }
    if (argc != 2) {
        fputs("Usage: foj-coll-validate PATH_TO_LOCAL_MAP.coll\n", stderr);
        return 2;
    }
    FILE *file = fopen(argv[1], "rb");
    if (!file) {
        perror("Unable to open COLL");
        return 2;
    }
    int status = 2;
    FojCollGrid *grid = malloc(sizeof(*grid));
    if (!grid) {
        fclose(file);
        return 2;
    }
    if (fseek(file, 0, SEEK_END) != 0) goto done;
    long length = ftell(file);
    if (length < 1 || length > FOJ_COLL_MAX_FILE_BYTES) goto done;
    if (fseek(file, 0, SEEK_SET) != 0) goto done;
    char *data = malloc((size_t)length);
    if (!data) goto done;
    if (fread(data, 1, (size_t)length, file) != (size_t)length) {
        free(data);
        goto done;
    }
    FojCollStatus parsed = foj_coll_parse(data, (size_t)length, grid);
    free(data);
    if (parsed != FOJ_COLL_OK) {
        fprintf(stderr, "COLL parse rejected: %s\n", foj_coll_error(parsed));
        goto done;
    }
    double low = HUGE_VAL, high = -HUGE_VAL;
    int nonzero = 0, varied = 0, flags[2] = {0, 0};
    for (int y = 0; y < grid->height; ++y) {
        for (int x = 0; x < grid->width; ++x) {
            float mincell = INFINITY, maxcell = -INFINITY;
            for (int n = 0; n < 4; ++n) {
                float value = grid->samples[y][x][n];
                if (value < mincell) mincell = value;
                if (value > maxcell) maxcell = value;
            }
            if (mincell < low) low = mincell;
            if (maxcell > high) high = maxcell;
            nonzero += mincell != 0.0f || maxcell != 0.0f;
            varied += mincell != maxcell;
            flags[0] += grid->flags[y][x][0] != 0;
            flags[1] += grid->flags[y][x][1] != 0;
        }
    }
    printf("Grid: %d x %d (%d cells)\n",
           grid->width, grid->height, grid->width * grid->height);
    printf("Origin: %.3f, %.3f; step: %.3f, %.3f\n",
           grid->origin[0], grid->origin[1], grid->step[0], grid->step[1]);
    printf("Raw numeric range: %.6f .. %.6f\n", low, high);
    printf("Nonzero / varied: %d / %d\n", nonzero, varied);
    printf("Raw true flag counts: %d / %d\n", flags[0], flags[1]);
    status = 0;
done:
    fclose(file);
    free(grid);
    return status;
}
