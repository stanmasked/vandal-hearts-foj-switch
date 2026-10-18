#ifndef FOJ_LOCAL_COLL_WINDOW_H
#define FOJ_LOCAL_COLL_WINDOW_H

/* Owner-local file input for a raw diagnostic panel, never gameplay rules.
 * The caller controls SD mounting; missing data is a normal condition. */
#include <stdbool.h>
#include "coll_battle_window.h"

bool foj_local_coll_load_path(const char *path, FojCollBattleWindow *window);

#endif
