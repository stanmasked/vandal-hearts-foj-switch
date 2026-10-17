/* Generated-only stage-164 DDS status-screen phase/color regressions. */
#ifdef NDEBUG
#undef NDEBUG
#endif
#include <assert.h>
#include <math.h>
#include <stdio.h>
#include "dds_screen_status.h"

static void test_legend(void) {
    const float expected[][4]={
        {0.65f,0.07f,0.13f,1.f},
        {0.10f,0.34f,0.84f,1.f},
        {0.72f,0.12f,0.63f,1.f},
        {0.91f,0.08f,0.09f,1.f},
        {0.96f,0.35f,0.12f,1.f},
        {1.0f,0.68f,0.07f,1.f},
        {0.06f,0.75f,0.24f,1.f}
    };
    float out[4]={0};
    assert(FOJ_GPU_DDS_STATUS_FRAMES_PER_SLOT==120);
    for(unsigned status=0;status<7;++status) {
        assert(foj_gpu_dds_status_color((FojAtlasDdsStatus)status,out));
        for(unsigned ch=0;ch<4;++ch) {
            assert(fabsf(out[ch]-expected[status][ch])<0.00001f);
            assert(out[ch]>=0.f&&out[ch]<=1.f);
        }
    }
    float untouched[4]={9.f,8.f,7.f,6.f};
    assert(!foj_gpu_dds_status_color((FojAtlasDdsStatus)111,untouched));
    assert(!foj_gpu_dds_status_color(FOJ_ATLAS_DDS_LOADED,NULL));
    assert(untouched[0]==9.f&&untouched[3]==6.f);
}
static void test_two_successful_materials(void) {
    unsigned slot=77;
    for(uint64_t frame=0;frame<120;++frame) {
        assert(foj_gpu_dds_status_screen(frame,2,0,&slot)==1);
        assert(slot==0);
    }
    for(uint64_t frame=120;frame<240;++frame) {
        assert(foj_gpu_dds_status_screen(frame,2,0,&slot)==1);
        assert(slot==1);
    }
    slot=77;
    assert(foj_gpu_dds_status_screen(240,2,0,&slot)==0);
    assert(slot==77);
    assert(foj_gpu_dds_status_screen(UINT64_MAX,2,0,&slot)==0);
}
static void test_fail_closed_visible_status(void) {
    unsigned slot=77;
    for(uint64_t frame=0;frame<3000;frame+=17) {
        assert(foj_gpu_dds_status_screen(frame,1,1,&slot)==1);
        assert(slot==0); /* early file0 failure */
        assert(foj_gpu_dds_status_screen(frame,2,1,&slot)==1);
        assert(slot==(frame<120?0u:1u)); /* file1 failure */
    }
    assert(foj_gpu_dds_status_screen(UINT64_MAX,2,1,&slot)==1);
    assert(slot==1);
}
static void test_invalid_queries_preserve_outputs(void) {
    unsigned slot=17;
    assert(foj_gpu_dds_status_screen(0,0,0,&slot)==-1);
    assert(foj_gpu_dds_status_screen(0,3,0,&slot)==-1);
    assert(foj_gpu_dds_status_screen(0,1,2,&slot)==-1);
    assert(foj_gpu_dds_status_screen(0,1,0,NULL)==-1);
    assert(slot==17);
}
int main(void) {
    test_legend();
    test_two_successful_materials();
    test_fail_closed_visible_status();
    test_invalid_queries_preserve_outputs();
    puts("Stage 164 GPU DDS status-screen legend and timing: PASS");
    return 0;
}
