#ifndef FOJ_COLL_GRID_H
#define FOJ_COLL_GRID_H

/* Portable reader for the *observed structure* of PS3 .coll map files.
 * Four numeric samples and two boolean fields are deliberately unnamed:
 * their original in-game meanings have not been verified.
 * No Konami assets are built into this library.
 */
#include <stddef.h>
#include <stdint.h>

enum { FOJ_COLL_MAX_SIDE = 64, FOJ_COLL_MAX_FILE_BYTES = 1048576 };

typedef struct {
    int width, height;
    float origin[2], step[2];
    float samples[FOJ_COLL_MAX_SIDE][FOJ_COLL_MAX_SIDE][4];
    uint8_t flags[FOJ_COLL_MAX_SIDE][FOJ_COLL_MAX_SIDE][2];
} FojCollGrid;

typedef enum {
    FOJ_COLL_OK = 0,
    FOJ_COLL_ARGUMENT,
    FOJ_COLL_LIMIT,
    FOJ_COLL_FORMAT,
    FOJ_COLL_DIMENSIONS,
    FOJ_COLL_COORDINATES,
    FOJ_COLL_COUNT
} FojCollStatus;

/* The output must be writable; it is modified on success and may be partially
 * modified on failure. Validate status before consuming it. */
FojCollStatus foj_coll_parse(const char *source, size_t length, FojCollGrid *out);
const char *foj_coll_error(FojCollStatus status);

#endif
