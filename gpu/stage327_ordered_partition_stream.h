#ifndef FOJ_STAGE327_ORDERED_PARTITION_STREAM_H
#define FOJ_STAGE327_ORDERED_PARTITION_STREAM_H

#include "stage325_corner_tile_partition.h"
#include "gpu_vertex_stream.h"

enum {
    FOJ_STAGE327_MAX_SOURCE_TRIANGLES=32u,
    FOJ_STAGE327_MAX_VERTICES=
        FOJ_STAGE327_MAX_SOURCE_TRIANGLES*
        (FOJ_STAGE325_TILE_VERTICES+FOJ_STAGE325_REMAINDER_VERTICES),
    FOJ_STAGE327_MAX_SECTIONS=FOJ_STAGE327_MAX_SOURCE_TRIANGLES*2u
};

typedef struct {
    uint32_t source_triangles;
    uint32_t output_vertices;
    uint32_t output_sections;
    uint32_t tile_fragments;
    uint32_t remainder_fragments;
    uint32_t tile_triangles;
    uint32_t remainder_triangles;
    uint8_t reserved[28];
} FojStage327StreamReport;

/* Build one ordered GPU-independent stream for a bounded batch of source
 * triangles, all using the same source atlas and one generated corner tile.
 *
 * Each source triangle is partitioned by Stage325. Its remainder fragment(s)
 * are appended first with source_texture_index, followed immediately by its
 * tile fragment(s) with tile_texture_index. This preserves source-triangle
 * order; the two regions of a single triangle have disjoint positive area.
 * Empty pieces are omitted. Sections are deliberately not merged across
 * source triangles, so transparent shape order stays explicit.
 *
 * The output can be passed as one whole stream to foj_gpu_prepare_stream:
 * its shared camera-depth range is computed across both materials and every
 * fragment, while returned batches retain the section sequence.
 *
 * All arguments are preflighted before outputs change. Inputs must not be
 * concurrently mutated during the call. Capacities must cover the worst-case
 * bounded output for source_triangle_count (57 vertices and two sections per
 * source triangle), and must not exceed the global fixed limits.
 *
 * Returns 1 on success, 0 on invalid input, insufficient capacity, aliasing,
 * or an invalid partition. Failed preflight leaves vertices, sections and
 * report unchanged. This does not bind textures or issue GPU commands.
 */
int foj_stage327_build_ordered_partition_stream(
    const FojStage325Triangle *triangles,
    size_t source_triangle_count,
    unsigned junction_page_x,
    unsigned junction_page_y,
    unsigned source_texture_index,
    unsigned tile_texture_index,
    size_t texture_count,
    FojTexturedVertex *vertices_out,
    size_t vertex_capacity,
    FojTextureSection *sections_out,
    size_t section_capacity,
    FojStage327StreamReport *report_out);

#endif
