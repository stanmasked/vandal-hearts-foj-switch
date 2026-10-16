#ifndef FOJ_OBJ_WIREFRAME_H
#define FOJ_OBJ_WIREFRAME_H

/* Portable, bounded triangle-soup OBJ reader and diagnostic wireframe.
 * No copyrighted game asset is embedded or downloaded.
 * Only positive 1-based triangular 'f v/vt/vn' and basic 'v x y z' supported.
 */
#include <stdio.h>
#include <stddef.h>
#include <stdint.h>

enum {
    FOJ_OBJ_MAX_VERTICES = 20000,
    FOJ_OBJ_MAX_TRIANGLES = 20000
};

typedef struct { float x, y, z; } FojVec3;
typedef struct { uint16_t a, b, c; } FojTri;

typedef struct {
    FojVec3 vertices[FOJ_OBJ_MAX_VERTICES];
    FojTri faces[FOJ_OBJ_MAX_TRIANGLES];
    size_t vertex_count, triangle_count;
    float center[3], radius;
} FojObjMesh;

/* Returns 0 success, nonzero malformed/unsupported/too large.
 * FojObjMesh should be allocated on heap, not on a small stack. */
int foj_obj_read(FILE *source, FojObjMesh *mesh);
void foj_obj_synthetic_cube(FojObjMesh *mesh);

/* 1280x720 linear framebuffer compatible. Does not draw text.
 * Simple no-depth wireframe; not the original FoJ renderer. */
void foj_obj_wireframe(const FojObjMesh *mesh, uint32_t *pixels,
                       int width, int height, int stride,
                       float yaw, float pitch, float zoom);

#endif
