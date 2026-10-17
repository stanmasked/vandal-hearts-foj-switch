#include "dds_command_plan.h"
#include "dds_screen_status.h"
#include "smoke_plan.h"
#include <stddef.h>

static int valid_status(FojAtlasDdsStatus value) {
    return value>=FOJ_ATLAS_DDS_INVALID_ARGUMENT &&
           value<=FOJ_ATLAS_DDS_LOADED;
}
static int healthy_status(FojAtlasDdsStatus value) {
    return value==FOJ_ATLAS_DDS_MISSING || value==FOJ_ATLAS_DDS_LOADED;
}

int foj_gpu_dds_frame_command(uint64_t frame,unsigned acquired_buffer,
                              const FojAtlasDdsStatus statuses[2],
                              unsigned observed_slots,int fatal,
                              FojGpuDdsFrameCommand *out) {
    if (!out||!statuses||acquired_buffer>=FOJ_GPU_DDS_SWAP_BUFFERS ||
        observed_slots<1u||observed_slots>FOJ_GPU_DDS_MATERIAL_SLOTS ||
        (fatal!=0&&fatal!=1) ||
        (!fatal&&observed_slots!=FOJ_GPU_DDS_MATERIAL_SLOTS))
        return 0;
    for (unsigned i=0;i<observed_slots;++i) {
        if (!valid_status(statuses[i]))return 0;
        if (fatal) {
            if (i+1u==observed_slots) {
                if (healthy_status(statuses[i]))return 0;
            } else if (!healthy_status(statuses[i]))return 0;
        } else if (!healthy_status(statuses[i]))return 0;
    }
    unsigned material=0;
    const int choice=foj_gpu_dds_status_screen(
        frame,observed_slots,fatal,&material);
    if (choice<0)return 0;
    FojGpuDdsFrameCommand candidate={
        choice?FOJ_GPU_DDS_LIST_STATUS:FOJ_GPU_DDS_LIST_SCENE,
        acquired_buffer,
        choice?material:foj_smoke_color_for_frame(frame)
    };
    if (candidate.index>=2u)return 0;
    *out=candidate;
    return 1;
}
