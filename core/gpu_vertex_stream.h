#ifndef FOJ_GPU_VERTEX_STREAM_H
#define FOJ_GPU_VERTEX_STREAM_H

/* GPU-independent per-material draw stream for FoJ research viewers.
 * Converts CPU-skinned XYZ/UV triangle soup to clip-space vertices and
 * ordered atlas draw batches. Does NOT issue GPU commands or embed PS3 data.
 */
#include <stddef.h>
#include <stdint.h>
#include "textured_triangles.h"

#define FOJ_GPU_MAX_VERTICES 20000u
#define FOJ_GPU_MAX_BATCHES 64u
#define FOJ_GPU_MAX_TEXTURES 8u

typedef struct { float x,y,z,w,u,v; } FojGpuVertex;
typedef struct { uint32_t first_vertex,vertex_count,texture_index; } FojGpuBatch;
typedef struct { size_t vertices_written,batches_written;
    float camera_depth_min,camera_depth_max; } FojGpuStreamInfo;
typedef enum {
    FOJ_GPU_STREAM_OK=0,FOJ_GPU_STREAM_ARGUMENT,
    FOJ_GPU_STREAM_BOUNDS,FOJ_GPU_STREAM_INVALID
} FojGpuStreamStatus;

/* Conversion matches current experimental CPU orthographic projection.
 * XY coordinates use [-1,1]. Z is normalized into [0.01,0.99] for
 * default deko3d 0-to-1 clip-depth. To preserve CPU z-ordering,
 * the future GPU pipeline must clear depth to 0 and compare GREATER.
 * The depth range is fitted to this one mesh/frame, not a whole scene.
 * Outputs may not alias inputs; failure changes no output values.
 */
FojGpuStreamStatus foj_gpu_prepare_stream(
    const FojTexturedVertex *input,size_t vertex_count,
    const FojTextureSection *sections,size_t section_count,
    size_t texture_count,const FojTextureCamera *camera,
    unsigned framebuffer_width,unsigned framebuffer_height,
    FojGpuVertex *vertices_out,size_t vertex_capacity,
    FojGpuBatch *batches_out,size_t batch_capacity,
    FojGpuStreamInfo *result);

#endif
