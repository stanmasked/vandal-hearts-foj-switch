#ifndef FOJ_GPU_DDS_COMMAND_PLAN_H
#define FOJ_GPU_DDS_COMMAND_PLAN_H
/* Platform-neutral command-list choice for synthetic GPU DDS bring-up.
 * Does not contain any game data, deko3d types, filesystem paths or logs. */
#include <stdint.h>
#include "atlas_dds.h"

enum {
    FOJ_GPU_DDS_LIST_STATUS=1,
    FOJ_GPU_DDS_LIST_SCENE=2,
    FOJ_GPU_DDS_SWAP_BUFFERS=2,
    FOJ_GPU_DDS_MATERIAL_SLOTS=2
};
typedef struct {
    unsigned kind;         /* STATUS or SCENE */
    unsigned buffer;       /* actual acquired swapchain buffer 0 or 1 */
    unsigned index;        /* status material slot or scene clear-color phase */
} FojGpuDdsFrameCommand;

/* Return 1 for a validated status/scene selection and 0 for invalid state.
 * Does not modify *out on rejection. Requires both statuses for a normal
 * scene; a fatal DDS failure must be the last observed status, after zero or
 * one successful material. Never selects an unrecorded/invalid command list.
 * The caller must check the actual recorded DkCmdList before submitting. */
int foj_gpu_dds_frame_command(uint64_t frame,unsigned acquired_buffer,
                              const FojAtlasDdsStatus statuses[2],
                              unsigned observed_slots,int fatal,
                              FojGpuDdsFrameCommand *out);
#endif
