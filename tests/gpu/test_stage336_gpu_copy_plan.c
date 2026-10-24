#include "stage336_gpu_copy_plan.h"
#include <assert.h>
#include <stdio.h>
#include <stdint.h>
#include <string.h>

static FojStage332DdsInfo img(unsigned width,unsigned height) {
    const FojStage332DdsInfo d={width,height,1u,FOJ_STAGE332_BC2,
        (size_t)width*height*4u};
    return d;
}
static void odd_and_large(void) {
    FojStage332DdsInfo d=img(74u,81u);
    FojStage336GpuCopyPlan p={0};
    assert(foj_stage336_gpu_copy_plan(&d,d.rgba_bytes,64u,524289u,512u,&p));
    assert(p.rows.row_length_pixels==80u && p.rows.row_pitch_bytes==320u);
    assert(p.rows.staging_bytes==25920u);
    assert(p.staging_allocation_bytes==28672u);
    assert(p.image_allocation_bytes==528384u);
    assert(p.image_alignment_bytes==4096u);
    d=img(2048u,2048u);
    assert(foj_stage336_gpu_copy_plan(&d,d.rgba_bytes,4096u,
                                     16809984u,65536u,&p));
    assert(p.rows.row_length_pixels==2048u);
    assert(p.rows.staging_bytes==16777216u);
    assert(p.staging_allocation_bytes==16777216u);
    assert(p.image_allocation_bytes==16842752u);
    assert(p.image_alignment_bytes==65536u);
}
static void refuse_without_mutation(void) {
    FojStage332DdsInfo d=img(73u,81u);
    FojStage336GpuCopyPlan original;
    memset(&original,0x7a,sizeof(original));
    FojStage336GpuCopyPlan p=original;
    assert(!foj_stage336_gpu_copy_plan(NULL,d.rgba_bytes,64u,1000u,4096u,&p));
    assert(!foj_stage336_gpu_copy_plan(&d,d.rgba_bytes,16u,1000u,4096u,&p));
    assert(!foj_stage336_gpu_copy_plan(&d,d.rgba_bytes,37u,1000u,4096u,&p));
    assert(!foj_stage336_gpu_copy_plan(&d,d.rgba_bytes,8192u,1000u,4096u,&p));
    assert(!foj_stage336_gpu_copy_plan(&d,d.rgba_bytes-1u,64u,1000u,4096u,&p));
    assert(!foj_stage336_gpu_copy_plan(&d,d.rgba_bytes,64u,0u,4096u,&p));
    assert(!foj_stage336_gpu_copy_plan(&d,d.rgba_bytes,64u,
                                    UINT64_MAX,4096u,&p));
    assert(!foj_stage336_gpu_copy_plan(&d,d.rgba_bytes,64u,1000u,3u,&p));
    assert(!foj_stage336_gpu_copy_plan(&d,d.rgba_bytes,64u,1000u,
                                    2u*1024u*1024u,&p));
    d.width=2049u;
    assert(!foj_stage336_gpu_copy_plan(&d,d.rgba_bytes,64u,1000u,4096u,&p));
    assert(memcmp(&p,&original,sizeof(p))==0);
}
static void bounds(void){
    FojStage332DdsInfo d=img(8u,8u);
    FojStage336GpuCopyPlan p={0};
    assert(foj_stage336_gpu_copy_plan(&d,256u,32u,
                                    FOJ_STAGE336_MAX_IMAGE_BYTES,4096u,&p));
    assert(p.image_allocation_bytes==FOJ_STAGE336_MAX_IMAGE_BYTES);
    assert(!foj_stage336_gpu_copy_plan(&d,256u,32u,
                                     FOJ_STAGE336_MAX_IMAGE_BYTES+1ull,
                                     4096u,&p));
}
int main(void){
    odd_and_large();refuse_without_mutation();bounds();
    puts("STAGE336_GENERATED_DYNAMIC_IMAGE_COPY_PLAN_PASS");
    return 0;
}
