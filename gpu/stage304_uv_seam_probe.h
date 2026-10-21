#ifndef FOJ_STAGE304_UV_SEAM_PROBE_H
#define FOJ_STAGE304_UV_SEAM_PROBE_H
/* Two side-by-side generated 1024 BC1 pages; no owner/PS3 assets.
 * Rear material is modified only after complete synthetic-input validation.
 * A guest GPU screenshot is needed to establish actual rendering. */
#include "private_bundle_intake.h"
#include "stage303_bc1_page_uv.h"
enum { FOJ_STAGE304_LEFT=0,FOJ_STAGE304_RIGHT=1 };
/* On failure, leave the source bundle and receipt untouched. */
int foj_stage304_apply_seam_probe(FojGpuPrivateBundleData *bundle,
                                  unsigned side,FojBc1PageUv *receipt);
#endif
