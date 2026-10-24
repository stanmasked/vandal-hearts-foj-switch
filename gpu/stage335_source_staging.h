#ifndef FOJ_STAGE335_SOURCE_STAGING_H
#define FOJ_STAGE335_SOURCE_STAGING_H
/* Host-testable linear RGBA8 staging, no original assets or GPU commands.
 * The real native deko3d buffer/image allocation is a separate gate. */
#include <stddef.h>
#include <stdint.h>
#include "stage332_dds_source.h"

enum {
    FOJ_STAGE335_MAX_STAGING_BYTES=2048u*2048u*4u,
    FOJ_STAGE335_MAX_ROW_ALIGNMENT=4096u
};

typedef struct {
    uint32_t width;
    uint32_t height;
    uint32_t row_length_pixels;
    uint32_t row_pitch_bytes;
    size_t rgba_bytes;
    size_t staging_bytes;
} FojStage335SourceStagingPlan;

/* Transactional: on failure out_plan remains exactly unchanged.
 * Alignments must be power-of-two bytes, >=4 and <=4096. This is only
 * the format/size stage, not verification of image device constraints. */
int foj_stage335_make_source_staging_plan(
    const FojStage332DdsInfo *verified_dds,
    size_t source_rgba_len,
    size_t destination_capacity,
    uint32_t row_alignment_bytes,
    FojStage335SourceStagingPlan *out_plan);

/* Fills only [0, plan.staging_bytes) of output with row-aligned RGBA;
 * all padding is zero. Never mutates destination on refusal.
 * Plan is recomputed and compared to reject forged/untrusted plans. */
int foj_stage335_stage_source_rgba(
    const FojStage332DdsInfo *verified_dds,
    const FojStage335SourceStagingPlan *plan,
    const uint8_t *source_rgba, size_t source_rgba_len,
    uint8_t *destination, size_t destination_capacity,
    uint32_t row_alignment_bytes);
#endif
