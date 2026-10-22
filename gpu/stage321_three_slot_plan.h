#ifndef FOJ_STAGE321_THREE_SLOT_PLAN_H
#define FOJ_STAGE321_THREE_SLOT_PLAN_H
/* Stage321: deterministic synthetic BC1 page residency planning for a
 * research GPU with exactly three simultaneous texture slots. This module
 * does NOT issue GPU commands or silently render four-page materials.
 * Stage320's sorted batch order is a planner order, NOT a transparency-
 * safe order for arbitrary original FoJ meshes.
 */
#include <stddef.h>
#include <stdint.h>
#include "stage320_uv_page_batches.h"
enum {
    FOJ_STAGE321_TEXTURE_SLOTS=3u,
    FOJ_STAGE321_EMPTY_PAGE=255u
};
typedef enum {
    FOJ_STAGE321_DIRECT=1,
    FOJ_STAGE321_PATCH_REQUIRED=2
} FojStage321Kind;
typedef struct {
    uint32_t batch_index;  /* corresponding Stage320 batch index */
    uint16_t geometry_mask;
    uint16_t filter_mask;
    uint16_t halo_mask;
    uint8_t kind;
    uint8_t bound_count;
    uint8_t uploaded_count;
    uint8_t reserved;
    /* AFTER command: retained resident page per physical slot, 255=empty.
     * PATCH_REQUIRED performs no uploads or binds; slot state is retained. */
    uint8_t resident_page[FOJ_STAGE321_TEXTURE_SLOTS];
    /* For DIRECT: page uploaded to the slot before binding; else 255.
     * For PATCH_REQUIRED: all 255 (no fabricated GPU preparation). */
    uint8_t uploaded_page[FOJ_STAGE321_TEXTURE_SLOTS];
    /* DIRECT: hardware slot IDs in ascending required page order.
     * Remaining positions and all PATCH_REQUIRED positions are 255. */
    uint8_t bound_slot[FOJ_STAGE321_TEXTURE_SLOTS];
} FojStage321Command;
typedef struct {
    unsigned commands;
    unsigned direct_batches;
    unsigned patch_required_batches;
    unsigned total_page_uploads;
    unsigned total_cached_binds;
    uint16_t all_direct_pages;
    uint16_t all_patch_required_pages;
    uint8_t final_resident_page[FOJ_STAGE321_TEXTURE_SLOTS];
    uint8_t reserved;
} FojStage321Report;

/* Consume one canonical Stage320 batch list (not arbitrary GPU draw order).
 * Direct commands may reference <= 3 distinct source pages and get explicit
 * slot bindings. Four-or-more page batches are conservatively DEFERRED:
 * PATCH_REQUIRED is not a draw and never binds a guessed substitute.
 *
 * Prior to writing output, validate ALL batches, sort order, indices,
 * masks, capacity, and aliasing. On ANY error return 0 without changing
 * commands or report. Never access original PS3 assets.
 */
int foj_stage321_plan_three_slots(
    const FojStage320Batch *batches,size_t batch_count,
    FojStage321Command *commands,size_t command_capacity,
    FojStage321Report *report);
#endif
