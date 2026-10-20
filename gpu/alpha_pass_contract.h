#ifndef FOJ_GPU_ALPHA_PASS_CONTRACT_H
#define FOJ_GPU_ALPHA_PASS_CONTRACT_H

/* Stage274: pure C11 fail-closed binding of a validated dynamic triangle
 * order to three exact GPU draw ranges, blend/depth states and texture IDs.
 * No deko3d SDK, no GPU calls, no original game content.
 *
 * Exactly one opaque rear material: texture 2 is first and writes depth.
 * Materials 0,1 must be translucent, depth test enabled/write disabled.
 * The caller separately validates each decoded DDS alpha (Stage273) and
 * verifies depth order using the independent Stage272 sorter.
 *
 * On any invalid input *out remains unchanged.
 */
#include <stddef.h>
#include <stdint.h>
#include "gpu_draw_plan.h"

enum { FOJ_GPU_ALPHA_PASS_COUNT=3 };
typedef enum {
    FOJ_GPU_ALPHA_PASS_OK=0,
    FOJ_GPU_ALPHA_PASS_INVALID=1,
    FOJ_GPU_ALPHA_PASS_UNSAFE=2
} FojGpuAlphaPassStatus;

typedef struct {
    uint32_t first_vertex;
    uint32_t vertex_count;
    uint32_t material_index;
    uint32_t blend_enabled;
    uint32_t depth_test_enabled;
    uint32_t depth_write_enabled;
} FojGpuAlphaPass;

FojGpuAlphaPassStatus foj_gpu_alpha_pass_contract(
    const FojGpuDrawRange *ranges,size_t range_count,
    const uint32_t *draw_order,size_t order_count,
    FojGpuAlphaPass *out,size_t out_capacity);

#endif
