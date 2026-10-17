/* Stage-167 synthetic shader boot diagnostics and acquire/list selection.
 * No actual GPU, shader bytecode, PS3 game source or hardware claims. */
#ifdef NDEBUG
#undef NDEBUG
#endif
#include <assert.h>
#include <math.h>
#include <stdio.h>
#include <stdint.h>
#include <string.h>
#include "gpu_boot_diagnostics.h"

static void check_colors_and_outcomes(void) {
    const float expected[][3]={
        {0.94f,0.35f,0.08f},
        {0.62f,0.11f,0.76f},
        {0.95f,0.65f,0.05f},
        {0.84f,0.08f,0.15f},
        {0.39f,0.06f,0.08f}
    };
    const char *labels[]={
        "shader code pool unavailable",
        "vertex DKSH unavailable or rejected",
        "fragment DKSH unavailable or rejected",
        "shader slot layout rejected",
        "deko3d shader stages rejected"
    };
    for (int value=1;value<=5;++value) {
        unsigned selected=99;
        float color[4]={9.f,8.f,7.f,6.f};
        assert(foj_gpu_boot_failure_frame(
            0,0,(FojGpuBootFailure)value,&selected,color));
        assert(selected==0);
        assert(!strcmp(foj_gpu_boot_failure_name((FojGpuBootFailure)value),
                       labels[value-1]));
        for(unsigned i=0;i<3;++i) {
            assert(fabsf(color[i]-expected[value-1][i])<0.00001f);
            assert(color[i]>=0.f&&color[i]<=1.f);
        }
        assert(color[3]==1.f);
    }
}

static void simulate_failure_presentations(void) {
    const unsigned gpu_lists[2][5]={
        {101,102,103,104,105},
        {201,202,203,204,205}
    };
    for (int status=1;status<=5;++status) {
        unsigned hits[2]={0,0};
        for (uint64_t frame=0;frame<4096;++frame) {
            /* Intentionally nonalternating buffer acquisition. */
            const unsigned acquired=(unsigned)((frame/5+frame/17)%2u);
            unsigned selected=99;
            float color[4]={0};
            assert(foj_gpu_boot_failure_frame(
                frame,acquired,(FojGpuBootFailure)status,&selected,color));
            const unsigned list=gpu_lists[selected][status-1];
            assert(selected==acquired);
            assert(list/100u==acquired+1u);
            assert(color[3]==1.f);
            hits[selected]++;
        }
        assert(hits[0]+hits[1]==4096);
        assert(hits[0]>0 && hits[1]>0);
        unsigned selected=99;
        float color[4]={0};
        assert(foj_gpu_boot_failure_frame(
            UINT64_MAX,1,(FojGpuBootFailure)status,&selected,color));
        assert(selected==1 && color[3]==1.f);
    }
}

static void invalid_input_preserves_outputs(void) {
    unsigned selected=17;
    float color[4]={3.f,4.f,5.f,6.f};
    assert(!foj_gpu_boot_failure_frame(
        0,2,FOJ_GPU_BOOT_VERTEX_DKSH,&selected,color));
    assert(!foj_gpu_boot_failure_frame(
        0,0,(FojGpuBootFailure)0,&selected,color));
    assert(!foj_gpu_boot_failure_frame(
        0,0,(FojGpuBootFailure)6,&selected,color));
    assert(!foj_gpu_boot_failure_frame(
        0,0,FOJ_GPU_BOOT_SHADER_STAGE,NULL,color));
    assert(!foj_gpu_boot_failure_frame(
        0,0,FOJ_GPU_BOOT_SHADER_STAGE,&selected,NULL));
    assert(selected==17);
    assert(color[0]==3.f && color[1]==4.f &&
           color[2]==5.f && color[3]==6.f);
    assert(!strcmp(foj_gpu_boot_failure_name((FojGpuBootFailure)17),
                   "unknown early GPU failure"));
}

int main(void) {
    check_colors_and_outcomes();
    simulate_failure_presentations();
    invalid_input_preserves_outputs();
    puts("Stage 167 shader boot diagnostic color and command plan: PASS");
    return 0;
}
