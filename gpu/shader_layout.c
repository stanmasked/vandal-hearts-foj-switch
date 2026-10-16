#include "shader_layout.h"

int foj_gpu_shader_layout(size_t vs_bytes, size_t fs_bytes,
                          FojGpuShaderLayout *out) {
    if (!out || vs_bytes < 512 || fs_bytes < 512 ||
        vs_bytes > FOJ_GPU_SHADER_MAX_DKSH ||
        fs_bytes > FOJ_GPU_SHADER_MAX_DKSH ||
        vs_bytes % FOJ_GPU_SHADER_ALIGNMENT ||
        fs_bytes % FOJ_GPU_SHADER_ALIGNMENT)
        return 0;

    const uint32_t vbase=0;
    const uint32_t fbase=FOJ_GPU_SHADER_SLOT_BYTES;
    const uint32_t tail_start=FOJ_GPU_SHADER_CODE_POOL-
                              FOJ_GPU_SHADER_CODE_TAIL;
    /* Uniform arithmetic in size_t avoids underflow/overflow. */
    if (vs_bytes > FOJ_GPU_SHADER_SLOT_BYTES-vbase ||
        fs_bytes > FOJ_GPU_SHADER_SLOT_BYTES ||
        (size_t)fbase+fs_bytes > tail_start)
        return 0;

    FojGpuShaderLayout result={
        FOJ_GPU_SHADER_CODE_POOL,vbase,fbase,
        (uint32_t)vs_bytes,(uint32_t)fs_bytes,tail_start
    };
    *out=result;
    return 1;
}
