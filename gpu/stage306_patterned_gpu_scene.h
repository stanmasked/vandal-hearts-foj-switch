#ifndef FOJ_STAGE306_PATTERNED_GPU_SCENE_H
#define FOJ_STAGE306_PATTERNED_GPU_SCENE_H
/* Stage306 generated-only UV interpolation and page-border continuity.
 * Decodes 2 real BC1 page buffers with 4 horizontal color bands apiece.
 * Adjacent page edges deliberately share cyan; no original PS3 inputs.
 */
#include "private_bundle_intake.h"
int foj_stage306_apply_patterned_split(FojGpuPrivateBundleData *bundle);
#endif
