#include "stage313_oriented_gutter.h"
#include "stage310_page_edge_gutter.h"
#include "stage311_horizontal_gutter.h"
#include <stdint.h>

static int overlaps(const void *aa,size_t an,const void *bb,size_t bn) {
    const uintptr_t a=(uintptr_t)aa,b=(uintptr_t)bb;
    if (an>UINTPTR_MAX-a || bn>UINTPTR_MAX-b)return 1;
    return a<b+bn && b<a+an;
}
int foj_stage313_build_oriented_gutter(
    FojStage313Edge orientation,
    const uint8_t *first,size_t first_bytes,
    const uint8_t *second,size_t second_bytes,
    uint8_t *output,size_t output_bytes,
    FojStage313GutterReport *report) {
    if ((orientation!=FOJ_STAGE313_EDGE_EAST &&
         orientation!=FOJ_STAGE313_EDGE_SOUTH) ||
        !first || !second || !output || !report ||
        first_bytes!=FOJ_BC1_PAGE_RGBA_BYTES ||
        second_bytes!=FOJ_BC1_PAGE_RGBA_BYTES ||
        output_bytes!=FOJ_BC1_PAGE_RGBA_BYTES ||
        overlaps(output,output_bytes,first,first_bytes) ||
        overlaps(output,output_bytes,second,second_bytes) ||
        overlaps(output,output_bytes,report,sizeof(*report)) ||
        overlaps(report,sizeof(*report),first,first_bytes) ||
        overlaps(report,sizeof(*report),second,second_bytes))
        return 0;

    FojStage313GutterReport local={orientation,0u,0u,0u};
    if (orientation==FOJ_STAGE313_EDGE_EAST) {
        FojStage310GutterReport native={0};
        if (!foj_stage310_build_page_edge_gutter(
                first,first_bytes,second,second_bytes,
                output,output_bytes,&native))
            return 0;
        local.samples_processed=native.rows;
        local.contrasting_samples=native.contrasting_edge_rows;
        local.genuinely_mixed_samples=native.strictly_mixed_rows;
    } else {
        FojStage311HorizontalReport native={0};
        if (!foj_stage311_build_horizontal_gutter(
                first,first_bytes,second,second_bytes,
                output,output_bytes,&native))
            return 0;
        local.samples_processed=native.columns_processed;
        local.contrasting_samples=native.contrasting_columns;
        local.genuinely_mixed_samples=native.genuinely_mixed_columns;
    }
    /* The native builder commits output only after complete validation;
     * the normalized report is then copied as the last operation. */
    *report=local;
    return 1;
}
