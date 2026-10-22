#ifndef FOJ_STAGE328_ATOMIC_CORNER_PATCH_STREAM_H
#define FOJ_STAGE328_ATOMIC_CORNER_PATCH_STREAM_H

#include "stage322_bounded_corner_tile.h"
#include "stage327_ordered_partition_stream.h"
#include "stage319_bilinear_halo_support.h"

enum {
    /* Keep the combined transaction's temporary vertex staging bounded for
     * the normal Switch application thread stack. */
    FOJ_STAGE328_MAX_SOURCE_TRIANGLES=16u,
    FOJ_STAGE328_MAX_VERTICES=
        FOJ_STAGE328_MAX_SOURCE_TRIANGLES*
        (FOJ_STAGE325_TILE_VERTICES+FOJ_STAGE325_REMAINDER_VERTICES),
    FOJ_STAGE328_MAX_SECTIONS=FOJ_STAGE328_MAX_SOURCE_TRIANGLES*2u
};

typedef struct {
    uint32_t atlas_first_x;
    uint32_t atlas_first_y;
    uint16_t source_page_mask;
    uint8_t page_id[4];
    uint8_t midpoint_rgba[4];
    uint32_t tile_bytes_written;
    uint64_t tile_fnv1a64;
    uint32_t source_triangles;
    uint32_t output_vertices;
    uint32_t output_sections;
    uint32_t tile_fragments;
    uint32_t remainder_fragments;
    uint32_t tile_triangles;
    uint32_t remainder_triangles;
    uint32_t source_texture_index;
    uint32_t tile_texture_index;
    uint8_t reserved[16];
} FojStage328Receipt;

/* Atomically prepare a generated 16x16 corner tile and its matching ordered
 * CPU-to-GPU geometry stream.
 *
 * batch must describe the supplied source_triangle_count triangles in their
 * Stage320 stable order. Its index_count must match the supplied count; each
 * triangle is independently checked against the batch's Stage319
 * geometry/filter/halo page masks. Only a four-page PATCH_REQUIRED corner
 * batch is accepted.
 *
 * decoded_pages are the batch's NW, NE, SW, SE decoded RGBA8 pages for the
 * selected internal atlas junction. They are read only and never embedded.
 * The source texture index identifies the original atlas/material used by
 * the remainder. The distinct tile texture index identifies the generated
 * 16x16 texture used by clipped tile fragments.
 *
 * This combined helper builds all outputs into bounded local staging first.
 * Any invalid mask, texture index, page, geometry, capacity or alias leaves
 * tile_out, vertices_out, sections_out and receipt_out unchanged. Caller
 * outputs must not overlap each other, inputs, page data or page descriptors.
 *
 * Capacities must cover the worst case (57 vertices and two sections per
 * triangle), within the fixed Stage328 limits. tile_capacity must equal
 * FOJ_STAGE322_TILE_BYTES. No allocation, file I/O or GPU command is issued.
 */
int foj_stage328_prepare_corner_patch_stream(
    const FojStage320Batch *batch,
    const FojStage325Triangle *source_triangles,
    size_t source_triangle_count,
    unsigned junction_page_x,
    unsigned junction_page_y,
    const uint8_t *const decoded_pages[4],
    const size_t decoded_lengths[4],
    unsigned source_texture_index,
    unsigned tile_texture_index,
    size_t texture_count,
    uint8_t *tile_out,
    size_t tile_capacity,
    FojTexturedVertex *vertices_out,
    size_t vertex_capacity,
    FojTextureSection *sections_out,
    size_t section_capacity,
    FojStage328Receipt *receipt_out);

#endif
