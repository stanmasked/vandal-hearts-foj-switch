#ifndef FOJ_STAGE305_SPLIT_GPU_SCENE_H
#define FOJ_STAGE305_SPLIT_GPU_SCENE_H
/* Generated-only single-frame, two-page BC1 quad research experiment.
 * The two page-local halves are separate triangles/batches meeting at x=0.
 * Does not authorize owner-original PS3 texture loading or bilinear stitching.
 */
#include "private_bundle_intake.h"

/* On refusal, bundle remains unchanged. All three source fixture RGBA slots
 * must be exact known synthetic Stage293 bytes and 9 generated vertices.
 * Success owns two new 256x256 BC1-decoded RGBA page buffers and 15 vertices.
 */
int foj_stage305_apply_split_surface(FojGpuPrivateBundleData *bundle);
#endif
