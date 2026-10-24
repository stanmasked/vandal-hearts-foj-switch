#ifndef FOJ_STAGE336_NATIVE_UPLOAD_H
#define FOJ_STAGE336_NATIVE_UPLOAD_H
/* Explicit opt-in native deko3d transfer; actual execution proof is separate. */
#include <deko3d.h>
#include "stage336_gpu_copy_plan.h"
typedef struct {
    DkMemBlock staging_mem;
    DkMemBlock image_mem;
    DkImage image;
    DkImageView image_view;
    FojStage336GpuCopyPlan plan;
} FojStage336NativeTexture;
/* Upon success, owns both memory blocks, and records ONE image-copy command.
 * No queue submission or render occurs. Keep resources alive until GPU idle.
 * out must be empty; caller releases only after queue completes. */
int foj_stage336_native_record_rgba_upload(
    DkDevice device,DkCmdBuf cmd,
    const FojStage332DdsInfo *source_info,
    const uint8_t *rgba,size_t rgba_size,
    uint32_t row_alignment,
    FojStage336NativeTexture *out);
void foj_stage336_native_release(FojStage336NativeTexture *texture);
#endif
