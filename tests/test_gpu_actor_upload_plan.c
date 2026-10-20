/* Stage256 generated-only, SDK-free GPU vertex memory and material plan. */
#ifdef NDEBUG
#undef NDEBUG
#endif
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include "actor_upload_plan.h"

static void check_plan(const FojGpuBatch *b,size_t nb,size_t nv,size_t nm,
                       size_t align,uint32_t payload,uint32_t allocated,
                       uint32_t mask) {
    FojGpuActorUploadPlan out;
    memset(&out,0xa5,sizeof(out));
    assert(foj_gpu_actor_upload_plan(b,nb,nv,nm,align,&out)==
           FOJ_GPU_STREAM_OK);
    assert(out.payload_bytes==payload);
    assert(out.allocation_bytes==allocated);
    assert(out.material_mask==mask);
    assert(out.batch_count==nb);
    assert(out.allocation_bytes>=out.payload_bytes);
    assert(out.allocation_bytes%align==0);
}

static void check_reject(const FojGpuBatch *b,size_t nb,size_t nv,
                         size_t nm,size_t align,FojGpuStreamStatus expected) {
    FojGpuActorUploadPlan out,unchanged;
    memset(&out,0xa5,sizeof(out));
    unchanged=out;
    assert(foj_gpu_actor_upload_plan(b,nb,nv,nm,align,&out)==expected);
    assert(memcmp(&out,&unchanged,sizeof(out))==0);
}

int main(void) {
    const FojGpuBatch quad[2]={{0,6,0},{6,6,1}};
    check_plan(quad,2,12,2,4096,288,4096,3);
    check_plan(quad,2,12,2,16,288,288,3);
    check_plan(quad,2,12,2,256,288,512,3);
    check_plan(quad,2,12,8,4096,288,4096,3);

    /* Future private multi-atlas Daldren scale; only invented batches:
     * six sections, two materials, 9,066 vertices, no original geometry. */
    const FojGpuBatch six[6]={
        {0,3000,0},{3000,3000,0},{6000,1500,0},
        {7500,1500,1},{9000,60,0},{9060,6,0}
    };
    check_plan(six,6,9066,2,4096,217584,221184,3);

    const FojGpuBatch maximum[1]={{0,19998,7}};
    check_plan(maximum,1,19998,8,4096,479952,483328,128);

    FojGpuBatch many[64];
    for(unsigned i=0;i<64;++i)
        many[i]=(FojGpuBatch){3u*i,3,i%8u};
    check_plan(many,64,192,8,4096,4608,8192,255);

    check_reject(NULL,2,12,2,4096,FOJ_GPU_STREAM_ARGUMENT);
    FojGpuActorUploadPlan dummy;
    assert(foj_gpu_actor_upload_plan(quad,2,12,2,4096,NULL)==
           FOJ_GPU_STREAM_ARGUMENT);
    (void)dummy;
    check_reject(quad,2,12,2,0,FOJ_GPU_STREAM_BOUNDS);
    check_reject(quad,2,12,2,8,FOJ_GPU_STREAM_BOUNDS);
    check_reject(quad,2,12,2,24,FOJ_GPU_STREAM_BOUNDS);
    check_reject(quad,2,12,2,1048577u,FOJ_GPU_STREAM_BOUNDS);
    check_reject(quad,0,12,2,4096,FOJ_GPU_STREAM_BOUNDS);
    check_reject(quad,2,0,2,4096,FOJ_GPU_STREAM_BOUNDS);
    check_reject(quad,2,13,2,4096,FOJ_GPU_STREAM_BOUNDS);
    check_reject(quad,2,20001,2,4096,FOJ_GPU_STREAM_BOUNDS);
    check_reject(quad,2,12,0,4096,FOJ_GPU_STREAM_BOUNDS);
    check_reject(quad,65,12,2,4096,FOJ_GPU_STREAM_BOUNDS);

    FojGpuBatch invalid[2]={{0,6,0},{6,6,1}};
    invalid[1].first_vertex=5;
    check_reject(invalid,2,12,2,4096,FOJ_GPU_STREAM_INVALID);
    invalid[1].first_vertex=9;
    check_reject(invalid,2,12,2,4096,FOJ_GPU_STREAM_INVALID);
    invalid[1].first_vertex=6;
    invalid[1].texture_index=2;
    check_reject(invalid,2,12,2,4096,FOJ_GPU_STREAM_INVALID);
    invalid[1].texture_index=1;
    invalid[1].vertex_count=3;
    check_reject(invalid,2,12,2,4096,FOJ_GPU_STREAM_INVALID);
    invalid[1].vertex_count=UINT32_MAX;
    check_reject(invalid,2,12,2,4096,FOJ_GPU_STREAM_INVALID);

    puts("Stage256 synthetic GPU actor upload: aligned memory and "
         "multi-material batches PASS");
    return 0;
}
