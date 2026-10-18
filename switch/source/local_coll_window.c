#include "local_coll_window.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/* Shared by console and isometric research NROs. The input bytes are
 * read into RAM, validated, then discarded. Never log or export them.
 * Large grid is static to avoid exceeding the Switch main stack. */
static FojCollGrid local_parsed_grid;

bool foj_local_coll_load_path(const char *path, FojCollBattleWindow *window) {
    if (!window) return false;
    memset(window, 0, sizeof(*window));
    if (!path) return false;
    FILE *file = fopen(path, "rb");
    if (!file) return false;
    bool ok = false;
    if (fseek(file, 0, SEEK_END) == 0) {
        long length = ftell(file);
        if (length > 0 && length <= FOJ_COLL_MAX_FILE_BYTES &&
            fseek(file, 0, SEEK_SET) == 0) {
            char *data = malloc((size_t)length);
            if (data) {
                if (fread(data, 1, (size_t)length, file) == (size_t)length &&
                    foj_coll_parse(data, (size_t)length,
                                   &local_parsed_grid) == FOJ_COLL_OK) {
                    const int w = local_parsed_grid.width;
                    const int h = local_parsed_grid.height;
                    if (w >= FOJ_WIDTH && h >= FOJ_HEIGHT) {
                        ok = foj_coll_battle_window(
                            &local_parsed_grid, (w-FOJ_WIDTH)/2,
                            (h-FOJ_HEIGHT)/2, window);
                    }
                }
                free(data);
            }
        }
    }
    if (fclose(file) != 0) ok = false;
    if (!ok) memset(window, 0, sizeof(*window));
    return ok;
}
