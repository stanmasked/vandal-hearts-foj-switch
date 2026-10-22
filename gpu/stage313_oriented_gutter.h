#ifndef FOJ_STAGE313_ORIENTED_GUTTER_H
#define FOJ_STAGE313_ORIENTED_GUTTER_H
/* Generated/research-only orientation dispatcher for a pair of already
 * decoded 256x256 BC1 RGBA pages. No PS3 source, device, or file access.
 * EAST: atlas pages (1,1)->(2,1), last x of left, first x of right.
 * SOUTH: atlas pages (1,1)->(1,2), last y of upper, first y of lower.
 * The caller supplies the pages in this exact source-to-destination order.
 */
#include <stddef.h>
#include <stdint.h>
#include "bc1_atlas_page.h"

typedef enum {
    FOJ_STAGE313_EDGE_EAST=1,
    FOJ_STAGE313_EDGE_SOUTH=2
} FojStage313Edge;

typedef struct {
    FojStage313Edge orientation;
    unsigned samples_processed;
    unsigned contrasting_samples;
    unsigned genuinely_mixed_samples;
} FojStage313GutterReport;

/* The output contains a gutter pair split at column 128 (EAST) or
 * row 128 (SOUTH). Original buffers and caller report remain untouched on
 * failure. Report/output alias with each other or either source refused.
 */
int foj_stage313_build_oriented_gutter(
    FojStage313Edge orientation,
    const uint8_t *first_rgba,size_t first_bytes,
    const uint8_t *second_rgba,size_t second_bytes,
    uint8_t *output_rgba,size_t output_bytes,
    FojStage313GutterReport *report);

#endif
