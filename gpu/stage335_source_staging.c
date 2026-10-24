#include "stage335_source_staging.h"
#include <stdint.h>
#include <string.h>

static int valid_format(FojStage332Format x) {
    return x == FOJ_STAGE332_BGRA8 || x == FOJ_STAGE332_BGR8 ||
           x == FOJ_STAGE332_BC1 || x == FOJ_STAGE332_BC2;
}
static int power_of_two(uint32_t n) {
    return n != 0u && (n & (n-1u)) == 0u;
}
int foj_stage335_make_source_staging_plan(
    const FojStage332DdsInfo *dds, size_t src_len,
    size_t dst_capacity, uint32_t alignment,
    FojStage335SourceStagingPlan *out) {
    if (!dds || !out || !valid_format(dds->format) ||
        dds->width == 0u || dds->height == 0u ||
        dds->width > FOJ_STAGE332_MAX_DIMENSION ||
        dds->height > FOJ_STAGE332_MAX_DIMENSION ||
        dds->mip_levels == 0u || dds->mip_levels > FOJ_STAGE332_MAX_MIPS ||
        !power_of_two(alignment) || alignment < 4u ||
        alignment > FOJ_STAGE335_MAX_ROW_ALIGNMENT)
        return 0;
    const uint64_t pixels = (uint64_t)dds->width * dds->height;
    if (pixels > FOJ_STAGE332_MAX_PIXELS) return 0;
    const uint64_t rgba = pixels * 4u;
    if (dds->rgba_bytes != rgba || src_len != rgba) return 0;
    const uint64_t row_bytes=(uint64_t)dds->width*4u;
    const uint64_t pitch=(row_bytes+alignment-1u)&~((uint64_t)alignment-1u);
    const uint64_t total=pitch*dds->height;
    if (total == 0u || total > FOJ_STAGE335_MAX_STAGING_BYTES ||
        total > dst_capacity || pitch > UINT32_MAX || pitch/4u > UINT32_MAX)
        return 0;
    const FojStage335SourceStagingPlan plan={
        dds->width, dds->height,
        (uint32_t)(pitch/4u), (uint32_t)pitch,
        (size_t)rgba,(size_t)total
    };
    *out=plan;
    return 1;
}
int foj_stage335_stage_source_rgba(
    const FojStage332DdsInfo *dds,
    const FojStage335SourceStagingPlan *plan,
    const uint8_t *src, size_t src_len,
    uint8_t *dst, size_t dst_capacity,
    uint32_t alignment) {
    if (!dds || !plan || !src || !dst) return 0;
    FojStage335SourceStagingPlan calculated;
    if (!foj_stage335_make_source_staging_plan(
            dds,src_len,dst_capacity,alignment,&calculated) ||
        plan->width != calculated.width ||
        plan->height != calculated.height ||
        plan->row_pitch_bytes != calculated.row_pitch_bytes ||
        plan->row_length_pixels != calculated.row_length_pixels ||
        plan->rgba_bytes != calculated.rgba_bytes ||
        plan->staging_bytes != calculated.staging_bytes)
        return 0;
    /* Reject overlap including partial overlaps; never decode in place. */
    const uintptr_t s=(uintptr_t)src, d=(uintptr_t)dst;
    if (s > UINTPTR_MAX-src_len || d > UINTPTR_MAX-calculated.staging_bytes ||
        (s < d+calculated.staging_bytes && d < s+src_len))
        return 0;
    const size_t row_bytes=(size_t)dds->width*4u;
    const size_t padding=(size_t)calculated.row_pitch_bytes-row_bytes;
    for (uint32_t y=0;y<dds->height;++y) {
        uint8_t *row=dst+(size_t)y*calculated.row_pitch_bytes;
        memcpy(row,src+(size_t)y*row_bytes,row_bytes);
        if (padding) memset(row+row_bytes,0,padding);
    }
    return 1;
}
