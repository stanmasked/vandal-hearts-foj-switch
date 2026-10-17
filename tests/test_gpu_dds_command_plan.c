/* Generated-only native DDS list submit/present simulation, no real GPU. */
#ifdef NDEBUG
#undef NDEBUG
#endif
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include "dds_command_plan.h"
#include "dds_screen_status.h"
#include "smoke_plan.h"

static const FojAtlasDdsStatus good[2]={FOJ_ATLAS_DDS_LOADED,FOJ_ATLAS_DDS_MISSING};
static const FojAtlasDdsStatus fail0[2]={FOJ_ATLAS_DDS_INVALID_FORMAT,FOJ_ATLAS_DDS_INVALID_ARGUMENT};
static const FojAtlasDdsStatus fail1[2]={FOJ_ATLAS_DDS_LOADED,FOJ_ATLAS_DDS_PATH_REJECTED};

static void expect(uint64_t frame,unsigned buffer,const FojAtlasDdsStatus states[2],
                   unsigned count,int fatal,unsigned kind,unsigned index) {
    FojGpuDdsFrameCommand plan={0};
    assert(foj_gpu_dds_frame_command(frame,buffer,states,count,fatal,&plan));
    assert(plan.kind==kind && plan.index==index && plan.buffer==buffer);
}
static void test_boundaries(void) {
    for(unsigned b=0;b<2;++b) {
        expect(0,b,good,2,0,FOJ_GPU_DDS_LIST_STATUS,0);
        expect(119,b,good,2,0,FOJ_GPU_DDS_LIST_STATUS,0);
        expect(120,b,good,2,0,FOJ_GPU_DDS_LIST_STATUS,1);
        expect(239,b,good,2,0,FOJ_GPU_DDS_LIST_STATUS,1);
        expect(240,b,good,2,0,FOJ_GPU_DDS_LIST_SCENE,0);
        expect(359,b,good,2,0,FOJ_GPU_DDS_LIST_SCENE,0);
        expect(360,b,good,2,0,FOJ_GPU_DDS_LIST_SCENE,1);
        expect(479,b,good,2,0,FOJ_GPU_DDS_LIST_SCENE,1);
        expect(UINT64_MAX,b,good,2,0,FOJ_GPU_DDS_LIST_SCENE,
               foj_smoke_color_for_frame(UINT64_MAX));
        expect(0,b,fail0,1,1,FOJ_GPU_DDS_LIST_STATUS,0);
        expect(120,b,fail0,1,1,FOJ_GPU_DDS_LIST_STATUS,0);
        expect(UINT64_MAX,b,fail0,1,1,FOJ_GPU_DDS_LIST_STATUS,0);
        expect(0,b,fail1,2,1,FOJ_GPU_DDS_LIST_STATUS,0);
        expect(120,b,fail1,2,1,FOJ_GPU_DDS_LIST_STATUS,1);
        expect(240,b,fail1,2,1,FOJ_GPU_DDS_LIST_STATUS,1);
        expect(UINT64_MAX,b,fail1,2,1,FOJ_GPU_DDS_LIST_STATUS,1);
    }
}
static void test_submit_present_sequences(void) {
    const unsigned status_lists[2][2]={{101,102},{201,202}};
    const unsigned scene_lists[2][2]={{103,104},{203,204}};
    const FojAtlasDdsStatus *cases[3]={good,fail0,fail1};
    const unsigned counts[3]={2,1,2};
    const int fatal[3]={0,1,1};
    for(unsigned scenario=0;scenario<3;++scenario) {
        unsigned status_count=0,scene_count=0,presented[2]={0,0};
        for(uint64_t frame=0;frame<4096;++frame) {
            /* Deliberately not just alternating images: honor acquire(). */
            const unsigned acquired=(unsigned)((frame*7u+frame/11u)%2u);
            FojGpuDdsFrameCommand plan={0};
            assert(foj_gpu_dds_frame_command(
                frame,acquired,cases[scenario],counts[scenario],
                fatal[scenario],&plan));
            assert(plan.buffer==acquired && plan.index<2);
            const unsigned cmd=plan.kind==FOJ_GPU_DDS_LIST_STATUS?
                status_lists[plan.buffer][plan.index]:
                scene_lists[plan.buffer][plan.index];
            assert(cmd>0 && cmd/100u==acquired+1u);
            if(plan.kind==FOJ_GPU_DDS_LIST_STATUS) {
                ++status_count;
                if(scenario==0 || scenario==2)
                    assert(plan.index==(unsigned)(frame>=120u));
                else assert(plan.index==0);
            } else {
                ++scene_count;
                assert(scenario==0 && frame>=240u);
                assert(plan.index==foj_smoke_color_for_frame(frame));
            }
            /* GPU submit and present apply to the same acquired buffer. */
            ++presented[acquired];
        }
        assert(presented[0]+presented[1]==4096u);
        if(scenario==0)
            assert(status_count==240u && scene_count==4096u-240u);
        else assert(status_count==4096u && scene_count==0u);
    }
}
static void test_invalid_rejected_transactionally(void) {
    FojGpuDdsFrameCommand plan={99,98,97};
    const FojAtlasDdsStatus bad0[2]={FOJ_ATLAS_DDS_INVALID_FORMAT,FOJ_ATLAS_DDS_LOADED};
    const FojAtlasDdsStatus bad1[2]={FOJ_ATLAS_DDS_LOADED,FOJ_ATLAS_DDS_LOADED};
    const FojAtlasDdsStatus bogus[2]={FOJ_ATLAS_DDS_LOADED,(FojAtlasDdsStatus)99};
    assert(!foj_gpu_dds_frame_command(0,0,good,2,0,NULL));
    assert(!foj_gpu_dds_frame_command(0,2,good,2,0,&plan));
    assert(!foj_gpu_dds_frame_command(0,0,NULL,2,0,&plan));
    assert(!foj_gpu_dds_frame_command(0,0,good,0,0,&plan));
    assert(!foj_gpu_dds_frame_command(0,0,good,3,0,&plan));
    assert(!foj_gpu_dds_frame_command(0,0,good,1,0,&plan));
    assert(!foj_gpu_dds_frame_command(0,0,good,2,2,&plan));
    assert(!foj_gpu_dds_frame_command(0,0,good,2,1,&plan));
    assert(!foj_gpu_dds_frame_command(0,0,bad0,2,1,&plan));
    assert(!foj_gpu_dds_frame_command(0,0,bad1,2,1,&plan));
    assert(!foj_gpu_dds_frame_command(0,0,bogus,2,0,&plan));
    assert(plan.kind==99 && plan.buffer==98 && plan.index==97);
}
int main(void) {
    test_boundaries();
    test_submit_present_sequences();
    test_invalid_rejected_transactionally();
    puts("Stage 165 DDS GPU command submit/present model: PASS");
    return 0;
}
