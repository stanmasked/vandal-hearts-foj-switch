#ifndef FOJ_GPU_BOOT_DIAGNOSTICS_H
#define FOJ_GPU_BOOT_DIAGNOSTICS_H
/* Generated-only two-buffer startup-error indicators for the research NRO.
 * Never decode FoJ data, expose SD paths or imply console verification. */
#include <stdint.h>
typedef enum {
    FOJ_GPU_BOOT_SHADER_CODE_MEMORY=1,
    FOJ_GPU_BOOT_VERTEX_DKSH=2,
    FOJ_GPU_BOOT_FRAGMENT_DKSH=3,
    FOJ_GPU_BOOT_SHADER_LAYOUT=4,
    FOJ_GPU_BOOT_SHADER_STAGE=5
} FojGpuBootFailure;
enum { FOJ_GPU_BOOT_SWAP_BUFFERS=2 };
/* Map a known startup failure and acquired image index to a flat color.
 * Returns 0 and leaves both outputs unchanged on invalid arguments.
 * A returned 1 means only a command has been selected, not that a
 * frame was actually shown by deko3d on a physical console. */
int foj_gpu_boot_failure_frame(uint64_t frame,unsigned acquired_buffer,
                                FojGpuBootFailure failure,
                                unsigned *selected_buffer,float color[4]);
const char *foj_gpu_boot_failure_name(FojGpuBootFailure failure);
#endif
