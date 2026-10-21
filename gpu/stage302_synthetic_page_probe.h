#ifndef FOJ_STAGE302_SYNTHETIC_PAGE_PROBE_H
#define FOJ_STAGE302_SYNTHETIC_PAGE_PROBE_H
/* Stage302 generated-only 1024 BC1 page GPU integration. NEVER accepts
 * external textures: validates exact generated three-material staging data
 * before modifying the rear material. No original PS3 assets are decoded. */
#include "private_bundle_intake.h"

enum {
    FOJ_STAGE302_PAGE_X=2,
    FOJ_STAGE302_PAGE_Y=1,
    FOJ_STAGE302_REAR_R=25,
    FOJ_STAGE302_REAR_G=202,
    FOJ_STAGE302_REAR_B=222
};

/* 1 = old generated rear replaced with one 256px RGBA page from the real
 * Stage301 C decoder. Failures do not modify the bundle. */
int foj_stage302_apply_generated_page(FojGpuPrivateBundleData *bundle);
#endif
