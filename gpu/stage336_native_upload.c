#include "stage336_native_upload.h"
#include <string.h>

int foj_stage336_native_record_rgba_upload(
    DkDevice device,DkCmdBuf cmd,const FojStage332DdsInfo *info,
    const uint8_t *rgba,size_t rgba_size,uint32_t row_alignment,
    FojStage336NativeTexture *out) {
    if (!device || !cmd || !info || !rgba || !out ||
        out->staging_mem || out->image_mem) return 0;
    /* No implicit original-source format, file I/O, or generated fallback. */
    if (row_alignment < DK_IMAGE_LINEAR_STRIDE_ALIGNMENT ||
        row_alignment % DK_IMAGE_LINEAR_STRIDE_ALIGNMENT) return 0;
    DkImageLayoutMaker maker;
    dkImageLayoutMakerDefaults(&maker,device);
    maker.type=DkImageType_2D;
    maker.format=DkImageFormat_RGBA8_Unorm;
    maker.dimensions[0]=info->width;
    maker.dimensions[1]=info->height;
    maker.dimensions[2]=1u;
    maker.mipLevels=1u; /* Stage334 independently checked level zero only. */
    /* Stage335 must reject malformed dimension values before using the SDK. */
    FojStage335SourceStagingPlan check;
    if (!foj_stage335_make_source_staging_plan(info,rgba_size,
         FOJ_STAGE335_MAX_STAGING_BYTES,row_alignment,&check)) return 0;
    DkImageLayout layout;
    dkImageLayoutInitialize(&layout,&maker);
    const uint64_t layout_bytes=dkImageLayoutGetSize(&layout);
    const uint32_t layout_align=dkImageLayoutGetAlignment(&layout);
    FojStage336GpuCopyPlan plan;
    if (!foj_stage336_gpu_copy_plan(info,rgba_size,row_alignment,
        layout_bytes,layout_align,&plan))return 0;
    DkMemBlockMaker staging_maker;
    dkMemBlockMakerDefaults(&staging_maker,device,
                            plan.staging_allocation_bytes);
    staging_maker.flags=DkMemBlockFlags_CpuUncached|DkMemBlockFlags_GpuCached;
    DkMemBlock staging=dkMemBlockCreate(&staging_maker);
    if (!staging)return 0;
    uint8_t *cpu=(uint8_t *)dkMemBlockGetCpuAddr(staging);
    DkGpuAddr gpu=dkMemBlockGetGpuAddr(staging);
    if (!cpu || gpu==DK_GPU_ADDR_INVALID ||
        gpu%DK_MEMBLOCK_ALIGNMENT ||
        !foj_stage335_stage_source_rgba(info,&plan.rows,rgba,rgba_size,
             cpu,plan.staging_allocation_bytes,row_alignment)) {
        dkMemBlockDestroy(staging);
        return 0;
    }
    DkMemBlockMaker img_maker;
    dkMemBlockMakerDefaults(&img_maker,device,plan.image_allocation_bytes);
    img_maker.flags=DkMemBlockFlags_GpuCached|DkMemBlockFlags_Image;
    DkMemBlock image_mem=dkMemBlockCreate(&img_maker);
    if (!image_mem) {
        dkMemBlockDestroy(staging);
        return 0;
    }
    if (dkMemBlockGetGpuAddr(image_mem)==DK_GPU_ADDR_INVALID) {
        dkMemBlockDestroy(image_mem);
        dkMemBlockDestroy(staging);
        return 0;
    }
    /* No command recorded before all inputs and GPU resources exist. */
    FojStage336NativeTexture temp={0};
    temp.staging_mem=staging;
    temp.image_mem=image_mem;
    temp.plan=plan;
    dkImageInitialize(&temp.image,&layout,image_mem,0);
    dkImageViewDefaults(&temp.image_view,&temp.image);
    /*
     * deko3d source/dk_image.cpp: DkCopyBuf.rowLength is a byte stride,
     * NOT a pixel count. imageHeight is a byte layer stride (0=default).
     * This single-layer RGBA8 copy must preserve the Stage335 byte pitch.
     */
    const DkCopyBuf src={gpu,plan.rows.row_pitch_bytes,0u};
    const DkImageRect rect={0u,0u,0u,plan.rows.width,
                            plan.rows.height,1u};
    dkCmdBufCopyBufferToImage(cmd,&src,&temp.image_view,&rect,0u);
    *out=temp;
    /* IMPORTANT: DkImageView points to out.image, not the temporary! */
    dkImageViewDefaults(&out->image_view,&out->image);
    return 1;
}
void foj_stage336_native_release(FojStage336NativeTexture *tex) {
    if(!tex)return;
    if(tex->image_mem)dkMemBlockDestroy(tex->image_mem);
    if(tex->staging_mem)dkMemBlockDestroy(tex->staging_mem);
    memset(tex,0,sizeof(*tex));
}
