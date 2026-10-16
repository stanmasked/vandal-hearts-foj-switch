#include "obj_wireframe.h"

#include <ctype.h>
#include <errno.h>
#include <math.h>
#include <stdlib.h>
#include <string.h>

enum { MAX_LINE = 1024 };

static int read_index(const char *token, unsigned *result) {
    if (!token || !isdigit((unsigned char)*token)) return 0;
    char *end = NULL;
    errno = 0;
    unsigned long number = strtoul(token, &end, 10);
    if (errno || !number || number > FOJ_OBJ_MAX_VERTICES) return 0;
    if (*end != '/' && *end != '\0') return 0;
    *result = (unsigned)number;
    return 1;
}

static int parse_vertex(char *line, FojVec3 *out) {
    char *cur = line + 2;
    float v[3];
    for (int i = 0; i < 3; ++i) {
        while (isspace((unsigned char)*cur)) ++cur;
        char *end = NULL;
        errno = 0;
        v[i] = strtof(cur, &end);
        if (errno == ERANGE || end == cur || !isfinite(v[i]) ||
            fabsf(v[i]) > 1000000.0f) return 0;
        cur = end;
    }
    while (isspace((unsigned char)*cur)) ++cur;
    if (*cur) return 0;
    out->x = v[0]; out->y = v[1]; out->z = v[2];
    return 1;
}

static int parse_face(char *line, FojTri *out, size_t n) {
    char *cur = line + 2;
    unsigned indexes[3];
    for (int i = 0; i < 3; ++i) {
        while (isspace((unsigned char)*cur)) ++cur;
        if (!*cur || !read_index(cur, &indexes[i]) || indexes[i] > n)
            return 0;
        while (*cur && !isspace((unsigned char)*cur)) ++cur;
    }
    while (isspace((unsigned char)*cur)) ++cur;
    if (*cur) return 0; /* Triangle only; no quads / polygons. */
    out->a = (uint16_t)(indexes[0] - 1);
    out->b = (uint16_t)(indexes[1] - 1);
    out->c = (uint16_t)(indexes[2] - 1);
    return 1;
}

static void recenter(FojObjMesh *mesh) {
    float lo[3] = {INFINITY, INFINITY, INFINITY};
    float hi[3] = {-INFINITY, -INFINITY, -INFINITY};
    for (size_t i = 0; i < mesh->vertex_count; ++i) {
        float values[3] = {
            mesh->vertices[i].x, mesh->vertices[i].y, mesh->vertices[i].z
        };
        for (int j = 0; j < 3; ++j) {
            if (values[j] < lo[j]) lo[j] = values[j];
            if (values[j] > hi[j]) hi[j] = values[j];
        }
    }
    mesh->radius = 0;
    for (int i = 0; i < 3; ++i) {
        mesh->center[i] = (lo[i] + hi[i]) * 0.5f;
        float extent = hi[i] - lo[i];
        if (extent > mesh->radius) mesh->radius = extent;
    }
    if (mesh->radius < 1e-5f) mesh->radius = 1;
}

int foj_obj_read(FILE *file, FojObjMesh *mesh) {
    if (!file || !mesh) return 1;
    mesh->vertex_count = mesh->triangle_count = 0;
    char line[MAX_LINE];
    while (fgets(line, sizeof(line), file)) {
        size_t len = strlen(line);
        if (!len) return 2;
        /* Reject overflow lines rather than accidentally parsing fragments. */
        if (line[len-1] != '\n' && !feof(file)) {
            int ch;
            while ((ch = fgetc(file)) != '\n' && ch != EOF) {}
            return 2;
        }
        if (line[0] == 'v' && line[1] == ' ') {
            if (mesh->vertex_count >= FOJ_OBJ_MAX_VERTICES ||
                !parse_vertex(line, &mesh->vertices[mesh->vertex_count]))
                return 3;
            mesh->vertex_count++;
        } else if (line[0] == 'f' && line[1] == ' ') {
            if (mesh->triangle_count >= FOJ_OBJ_MAX_TRIANGLES ||
                !parse_face(line, &mesh->faces[mesh->triangle_count],
                            mesh->vertex_count))
                return 4;
            mesh->triangle_count++;
        } else if (line[0] == '#' || line[0] == '\n' ||
                   line[0] == 'o' || line[0] == 'g' ||
                   (line[0] == 'v' && (line[1] == 'n' || line[1] == 't'))) {
            /* Object names, texture coordinates and normals are deliberately
               ignored in the *wireframe-only* diagnostic viewer. */
            continue;
        } else {
            return 5;
        }
    }
    if (ferror(file) || mesh->vertex_count < 3 || !mesh->triangle_count)
        return 6;
    recenter(mesh);
    return 0;
}

void foj_obj_synthetic_cube(FojObjMesh *mesh) {
    memset(mesh, 0, sizeof(*mesh));
    static const FojVec3 corners[] = {
        {-1,-1,-1}, {1,-1,-1}, {1,1,-1}, {-1,1,-1},
        {-1,-1, 1}, {1,-1, 1}, {1,1, 1}, {-1,1, 1}
    };
    static const FojTri faces[] = {
        {0,1,2},{0,2,3}, {4,6,5},{4,7,6},
        {0,4,5},{0,5,1}, {1,5,6},{1,6,2},
        {2,6,7},{2,7,3}, {3,7,4},{3,4,0}
    };
    memcpy(mesh->vertices, corners, sizeof(corners));
    memcpy(mesh->faces, faces, sizeof(faces));
    mesh->vertex_count = sizeof(corners)/sizeof(corners[0]);
    mesh->triangle_count = sizeof(faces)/sizeof(faces[0]);
    recenter(mesh);
}

static void put(uint32_t *p, int w, int h, int stride,
                int x, int y, uint32_t color) {
    if (x>=0 && y>=0 && x<w && y<h)
        p[(size_t)y*(size_t)stride+(size_t)x] = color;
}

static void edge(uint32_t *p, int w, int h, int stride,
                 int x0, int y0, int x1, int y1, uint32_t color) {
    int dx = abs(x1-x0), dy = abs(y1-y0);
    int sx = x0<x1 ? 1 : -1, sy = y0<y1 ? 1 : -1;
    int error = dx-dy;
    /* Bound iterations even for unexpectedly invalid projected values. */
    int budget = 10000;
    while (budget--) {
        put(p,w,h,stride,x0,y0,color);
        if (x0==x1 && y0==y1) break;
        int e=2*error;
        if (e>-dy) {error-=dy;x0+=sx;}
        if (e<dx) {error+=dx;y0+=sy;}
    }
}

void foj_obj_wireframe(const FojObjMesh *mesh, uint32_t *pixels,
                       int width, int height, int stride,
                       float yaw, float pitch, float zoom) {
    if (!mesh || !pixels || width<=0 || height<=0 || stride<width ||
        mesh->vertex_count>FOJ_OBJ_MAX_VERTICES ||
        mesh->triangle_count>FOJ_OBJ_MAX_TRIANGLES ||
        !isfinite(yaw) || !isfinite(pitch) || !isfinite(zoom) ||
        zoom<=0 || zoom>10 || mesh->radius<=0) return;
    for (int y=0; y<height; ++y)
        for (int x=0; x<width; ++x)
            pixels[(size_t)y*stride+x] = UINT32_C(0xff181c25);

    int *xs = malloc(mesh->vertex_count * sizeof(*xs));
    int *ys = malloc(mesh->vertex_count * sizeof(*ys));
    if (!xs || !ys) {free(xs);free(ys);return;}
    float cy=cosf(yaw), sy=sinf(yaw), cp=cosf(pitch), sp=sinf(pitch);
    float scale = ((width<height ? width:height)*0.82f / mesh->radius)*zoom;
    for (size_t i=0; i<mesh->vertex_count; ++i) {
        FojVec3 v = mesh->vertices[i];
        float x=v.x-mesh->center[0],y=v.y-mesh->center[1],z=v.z-mesh->center[2];
        float tx=cy*x+sy*z, tz=-sy*x+cy*z;
        float ty=cp*y-sp*tz;
        xs[i]=(int)(width/2 + tx*scale);
        ys[i]=(int)(height/2 - ty*scale);
    }
    for (size_t i=0; i<mesh->triangle_count; ++i) {
        FojTri f = mesh->faces[i];
        if (f.a>=mesh->vertex_count||f.b>=mesh->vertex_count||
            f.c>=mesh->vertex_count) continue;
        uint32_t color=UINT32_C(0xffbde4da);
        edge(pixels,width,height,stride,xs[f.a],ys[f.a],xs[f.b],ys[f.b],color);
        edge(pixels,width,height,stride,xs[f.b],ys[f.b],xs[f.c],ys[f.c],color);
        edge(pixels,width,height,stride,xs[f.c],ys[f.c],xs[f.a],ys[f.a],color);
    }
    free(xs);free(ys);
}
