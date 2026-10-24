#ifndef FOJ_STAGE336_GPU_COPY_PLAN_H
#define FOJ_STAGE336_GPU_COPY_PLAN_H
/* Synthetic-only GPU upload planning: no SDK calls or copyrighted material. */
#include <stddef.h>
#include <stdint.h>
#include "stage335_source_staging.h"
enum {
    FOJ_STAGE336_MEM_ALIGNMENT = 4096u,
    FOJ_STAGE336_MAX_IMAGE_BYTES = 64u * 1024u * 1024u,
    FOJ_STAGE336_MAX_IMAGE_ALIGNMENT = 1024u * 1024u
};
typedef struct {
    FojStage335SourceStagingPlan rows;
    uint32_t staging_allocation_bytes;
    uint32_t image_allocation_bytes;
    uint32_t image_alignment_bytes;
} FojStage336GpuCopyPlan;
/* layout bytes/alignment MUST come from actual dkImageLayout getters. This
 * planner cannot certify the native SDK/GPU copy. Refuse without mutations. */
int foj_stage336_gpu_copy_plan(
    const FojStage332DdsInfo *info, size_t rgba_bytes,
    uint32_t row_alignment_bytes,
    uint64_t image_layout_bytes, uint32_t image_layout_alignment,
    FojStage336GpuCopyPlan *out);
#endif
