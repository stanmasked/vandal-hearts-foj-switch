#ifndef FOJ_GPU_PRIVATE_BUNDLE_INTAKE_H
#define FOJ_GPU_PRIVATE_BUNDLE_INTAKE_H
/* Stage258: local-only, opt-in two-atlas preflight. Does NOT upload a
 * private vertex, draw the private actor, or persist proprietary bytes.
 * Paths must be fixed trusted local paths. No input is sent to CI.
 * The caller-owned output is transactionally written on complete success.
 */
#include "private_actor_bridge.h"
#include "atlas_dds.h"

enum { FOJ_GPU_PRIVATE_REQUIRED_ATLASES=2 };

typedef enum {
    FOJ_PRIVATE_BUNDLE_OK=0,
    FOJ_PRIVATE_BUNDLE_ARGUMENT,
    FOJ_PRIVATE_BUNDLE_MISSING,
    FOJ_PRIVATE_BUNDLE_PATH_REJECTED,
    FOJ_PRIVATE_BUNDLE_IO,
    FOJ_PRIVATE_BUNDLE_CHANGED,
    FOJ_PRIVATE_BUNDLE_INVALID,
    FOJ_PRIVATE_BUNDLE_MEMORY
} FojGpuPrivateBundleStatus;

typedef struct {
    FojGpuPrivateActorPlan actor;
    FojAtlasRgba8Info atlas[FOJ_GPU_PRIVATE_REQUIRED_ATLASES];
    unsigned atlas_count;
} FojGpuPrivateBundleReport;

/* Rejects missing/invalid parts, unsupported DDS formats, mismatched
 * FOJMAT texture count or corrupt FOJRM section mapping. Both atlases
 * are mandatory: there is NO silent synthetic fallback in private mode.
 * No paths, source bytes, hashes or names are written to *report.
 * Reports do not establish a simultaneous atomic snapshot across files.
 */
FojGpuPrivateBundleStatus foj_gpu_private_bundle_preflight(
    const char *mesh_path, const char *material_path,
    const char *const atlas_paths[FOJ_GPU_PRIVATE_REQUIRED_ATLASES],
    const FojTextureCamera *camera, unsigned width,unsigned height,
    size_t gpu_alignment,FojGpuPrivateBundleReport *report);

const char *foj_gpu_private_bundle_status_name(
    FojGpuPrivateBundleStatus status);
#endif
