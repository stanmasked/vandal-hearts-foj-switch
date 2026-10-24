#include "stage336_gpu_copy_plan.h"
#include <limits.h>

static int power2(uint32_t n) { return n && !(n & (n-1u)); }
static int aligned_bytes(uint64_t bytes,uint32_t alignment,uint32_t *out) {
    if (!bytes || !power2(alignment)) return 0;
    const uint64_t a=((bytes+(uint64_t)alignment-1u)/alignment)*alignment;
    if (a>UINT32_MAX || a>FOJ_STAGE336_MAX_IMAGE_BYTES) return 0;
    *out=(uint32_t)a;
    return 1;
}
int foj_stage336_gpu_copy_plan(
    const FojStage332DdsInfo *info,size_t rgba_bytes,
    uint32_t row_alignment_bytes,uint64_t image_layout_bytes,
    uint32_t image_alignment,FojStage336GpuCopyPlan *out) {
    if(!out || !info || !power2(row_alignment_bytes) ||
       row_alignment_bytes<32u || row_alignment_bytes>4096u ||
       !power2(image_alignment) || !image_alignment ||
       image_alignment>FOJ_STAGE336_MAX_IMAGE_ALIGNMENT ||
       image_layout_bytes>FOJ_STAGE336_MAX_IMAGE_BYTES)
        return 0;
    FojStage335SourceStagingPlan rows;
    if(!foj_stage335_make_source_staging_plan(
         info,rgba_bytes,FOJ_STAGE335_MAX_STAGING_BYTES,
         row_alignment_bytes,&rows))return 0;
    if (rows.row_length_pixels<info->width ||
        rows.row_pitch_bytes!=rows.row_length_pixels*4u)
        return 0;
    FojStage336GpuCopyPlan tmp={0};
    const uint32_t image_mem_alignment=image_alignment>FOJ_STAGE336_MEM_ALIGNMENT?
                                      image_alignment:FOJ_STAGE336_MEM_ALIGNMENT;
    if(!aligned_bytes(rows.staging_bytes,FOJ_STAGE336_MEM_ALIGNMENT,
                      &tmp.staging_allocation_bytes) ||
       !aligned_bytes(image_layout_bytes,image_mem_alignment,
                      &tmp.image_allocation_bytes))return 0;
    tmp.rows=rows;
    tmp.image_alignment_bytes=image_mem_alignment;
    *out=tmp;
    return 1;
}
