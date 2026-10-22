#ifndef FOJ_STAGE322_BOUNDED_CORNER_TILE_H
#define FOJ_STAGE322_BOUNDED_CORNER_TILE_H
/* Generated-only, bounded single-texture replacement for a validated
 * Stage321 four-page PATCH_REQUIRED batch at one internal atlas junction.
 * Does NOT draw, bind textures, infer original FoJ UVs, or publish assets.
 */
#include <stddef.h>
#include <stdint.h>
#include "stage321_three_slot_plan.h"
#include "bc1_atlas_page.h"

enum {
    FOJ_STAGE322_TILE_EDGE=16u,
    FOJ_STAGE322_TILE_BYTES=16u*16u*4u
};
typedef struct {
    uint32_t atlas_first_x; /* source texel x at tile pixel (0,0) */
    uint32_t atlas_first_y;
    uint16_t source_page_mask;
    uint8_t page_id[4]; /* NW,NE,SW,SE atlas page number, row-major */
    uint8_t midpoint_rgba[4]; /* precise bilinear value at junction */
    uint32_t bytes_written;
    uint64_t fnv1a64; /* checksum of exactly 1024 generated tile bytes */
} FojStage322TileReceipt;

/* Source page ids = (junction_page_y-1,junction_page_x-1), etc.
 * Junctions range [1..3] along both axes of a 4x4 page atlas.
 * The decoded 256x256 RGBA8 source page buffers are independent.
 *
 * A 16x16 RGBA8 tile copies the 8x8 nearest original texels from EACH
 * of four pages: 248..255 on the west/north and 0..7 on the east/south.
 * The GPU can then linearly sample this ONE tile with correct neighbors
 * around that corner. Tile coordinates use texel centers, not nearest
 * or made-up averaged colors. No GPU proof is claimed by this CPU API.
 *
 * Refuse non-four-way filter masks, commands not PATCH_REQUIRED, wrong
 * page sizes, any source alias or output/report/command alias, stale
 * bindings/uploads, invalid slot residency, wrong output byte length.
 * On failure, output tile and receipt remain entirely unchanged.
 */
int foj_stage322_build_bounded_corner_tile(
    const FojStage321Command *command,
    unsigned junction_page_x,unsigned junction_page_y,
    const uint8_t *const decoded_pages[4],
    const size_t decoded_lengths[4],
    uint8_t *tile_out,size_t tile_bytes,
    FojStage322TileReceipt *receipt);
#endif
