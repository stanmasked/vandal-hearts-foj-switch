#include "gpu_boot_diagnostics.h"
#include <stddef.h>

const char *foj_gpu_boot_failure_name(FojGpuBootFailure failure) {
    switch (failure) {
        case FOJ_GPU_BOOT_SHADER_CODE_MEMORY:
            return "shader code pool unavailable";
        case FOJ_GPU_BOOT_VERTEX_DKSH:
            return "vertex DKSH unavailable or rejected";
        case FOJ_GPU_BOOT_FRAGMENT_DKSH:
            return "fragment DKSH unavailable or rejected";
        case FOJ_GPU_BOOT_SHADER_LAYOUT:
            return "shader slot layout rejected";
        case FOJ_GPU_BOOT_SHADER_STAGE:
            return "deko3d shader stages rejected";
        default:
            return "unknown early GPU failure";
    }
}

int foj_gpu_boot_failure_frame(uint64_t frame,unsigned acquired_buffer,
                                FojGpuBootFailure failure,
                                unsigned *selected_buffer,float color[4]) {
    (void)frame; /* Persistent color until actual user exit. */
    if (!selected_buffer||!color ||
        acquired_buffer>=FOJ_GPU_BOOT_SWAP_BUFFERS)return 0;
    float temp[4];
    switch (failure) {
        case FOJ_GPU_BOOT_SHADER_CODE_MEMORY:
            temp[0]=0.94f;temp[1]=0.35f;temp[2]=0.08f;break; /* orange */
        case FOJ_GPU_BOOT_VERTEX_DKSH:
            temp[0]=0.62f;temp[1]=0.11f;temp[2]=0.76f;break; /* violet */
        case FOJ_GPU_BOOT_FRAGMENT_DKSH:
            temp[0]=0.95f;temp[1]=0.65f;temp[2]=0.05f;break; /* amber */
        case FOJ_GPU_BOOT_SHADER_LAYOUT:
            temp[0]=0.84f;temp[1]=0.08f;temp[2]=0.15f;break; /* red */
        case FOJ_GPU_BOOT_SHADER_STAGE:
            temp[0]=0.39f;temp[1]=0.06f;temp[2]=0.08f;break; /* deep red */
        default:
            return 0;
    }
    temp[3]=1.0f;
    for (unsigned i=0;i<4;++i)color[i]=temp[i];
    *selected_buffer=acquired_buffer;
    return 1;
}
