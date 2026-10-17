#ifndef FOJ_GPU_RESEARCH_MESH_H
#define FOJ_GPU_RESEARCH_MESH_H

/* Synthetic two-triangle research surface prepared through the actual
 * CPU-to-GPU geometry stream. No original FoJ meshes or textures.
 * This is a bridge experiment, NOT original game rendering. */
#include "gpu_vertex_stream.h"

enum {
    FOJ_RESEARCH_VERTEX_COUNT = 6,
    FOJ_RESEARCH_BATCH_COUNT = 1
};

FojGpuStreamStatus foj_gpu_research_mesh(
    FojGpuVertex *vertices, size_t vertex_capacity,
    FojGpuBatch *batches, size_t batch_capacity,
    FojGpuStreamInfo *info);

#endif
