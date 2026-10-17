#include "dds_screen_status.h"

int foj_gpu_dds_status_color(FojAtlasDdsStatus status,float rgba[4]) {
    if (!rgba)return 0;
    const float *color=NULL;
    static const float invalid_args[4]={0.65f,0.07f,0.13f,1.0f};
    static const float missing[4]={0.10f,0.34f,0.84f,1.0f};
    static const float path_rejected[4]={0.72f,0.12f,0.63f,1.0f};
    static const float io_failed[4]={0.91f,0.08f,0.09f,1.0f};
    static const float changed[4]={0.96f,0.35f,0.12f,1.0f};
    static const float invalid_format[4]={1.0f,0.68f,0.07f,1.0f};
    static const float loaded[4]={0.06f,0.75f,0.24f,1.0f};
    switch(status) {
        case FOJ_ATLAS_DDS_INVALID_ARGUMENT: color=invalid_args;break;
        case FOJ_ATLAS_DDS_MISSING: color=missing;break;
        case FOJ_ATLAS_DDS_PATH_REJECTED: color=path_rejected;break;
        case FOJ_ATLAS_DDS_IO_FAILURE: color=io_failed;break;
        case FOJ_ATLAS_DDS_SOURCE_CHANGED: color=changed;break;
        case FOJ_ATLAS_DDS_INVALID_FORMAT: color=invalid_format;break;
        case FOJ_ATLAS_DDS_LOADED: color=loaded;break;
        default:return 0;
    }
    for(unsigned i=0;i<4;++i)rgba[i]=color[i];
    return 1;
}

int foj_gpu_dds_status_screen(uint64_t frame,unsigned observed_slots,
                               int fatal,unsigned *material_slot) {
    if (!material_slot || observed_slots<1u || observed_slots>2u ||
        (fatal!=0 && fatal!=1))return -1;
    if (frame<FOJ_GPU_DDS_STATUS_FRAMES_PER_SLOT) {
        *material_slot=0;
        return 1;
    }
    if (observed_slots==2u &&
        frame<2u*(uint64_t)FOJ_GPU_DDS_STATUS_FRAMES_PER_SLOT) {
        *material_slot=1;
        return 1;
    }
    if (fatal) {
        *material_slot=observed_slots-1u;
        return 1;
    }
    return 0;
}
