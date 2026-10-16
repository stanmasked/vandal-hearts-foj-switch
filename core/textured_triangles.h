#ifndef FOJ_TEXTURED_TRIANGLES_H
#define FOJ_TEXTURED_TRIANGLES_H
/* Portable CPU textured triangle rasterizer: research-only.
 * Uses orthographic projection, nearest UV, alpha cutout, float z-buffer.
 * Original FoJ material/shader semantics and camera are still unknown.
 */
#include <stddef.h>
#include <stdint.h>

typedef struct {
    float x, y, z, u, v;
} FojTexturedVertex;

typedef struct {
    const uint32_t *rgba;
    unsigned width, height, stride;
} FojTexture;

typedef struct {
    uint32_t *rgba; /* 0xAABBGGRR */
    float *depth;
    unsigned width, height, color_stride, depth_stride;
} FojRenderSurface;

typedef struct {
    float center_x, center_y, center_z;
    float extent;
    float yaw, pitch, zoom;
    int flip_v; /* manually configured research texture orientation */
} FojTextureCamera;

typedef enum {
    FOJ_TEX_OK = 0,
    FOJ_TEX_ARGUMENT,
    FOJ_TEX_BOUNDS,
    FOJ_TEX_GEOMETRY
} FojTextureStatus;

/* Clears color/depth then draws every triangle. pixels_drawn counts
 * successful depth/alpha passes (a pixel may be counted more than once).
 * Caller owns output buffers; each stride is measured in elements.
 */
FojTextureStatus foj_textured_render(
    const FojTexturedVertex *vertices, size_t vertex_count,
    const FojTexture *texture, const FojRenderSurface *surface,
    const FojTextureCamera *camera, size_t *pixels_drawn);

#endif
