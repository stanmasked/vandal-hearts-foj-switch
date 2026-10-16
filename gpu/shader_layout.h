#ifndef FOJ_GPU_SHADER_LAYOUT_H
#define FOJ_GPU_SHADER_LAYOUT_H

/* Research-only UAM DKSH GPU code memory layout. No game assets.
 * Two disjoint 128-KiB slots in one 256-KiB DkMemBlockFlags_Code block.
 * Reserve deko3d's final 1 KiB unusable code tail and extra capacity
 * for possible alignment and compiler metadata. */
#include <stddef.h>
#include <stdint.h>

enum {
    FOJ_GPU_SHADER_CODE_POOL = 0x40000,
    FOJ_GPU_SHADER_SLOT_BYTES = 0x20000,
    FOJ_GPU_SHADER_MAX_DKSH = 0x1f000,
    FOJ_GPU_SHADER_CODE_TAIL = 0x400,
    FOJ_GPU_SHADER_ALIGNMENT = 0x100
};

typedef struct {
    uint32_t block_size;
    uint32_t vertex_offset;
    uint32_t fragment_offset;
    uint32_t vertex_size;
    uint32_t fragment_size;
    uint32_t protected_tail_start;
} FojGpuShaderLayout;

/* Returns 1 on success, 0 on invalid stage size/overlap/overflow.
 * Never modifies caller's output on error. Input byte counts include
 * the UAM DKSH control plus code sections (already stage-validated). */
int foj_gpu_shader_layout(size_t vs_bytes, size_t fs_bytes,
                          FojGpuShaderLayout *out);
#endif
