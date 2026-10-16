#include "textured_triangles.h"
#include <math.h>

/* CPU research render. No original PS3 material/shader data included. */
typedef struct { float x,y,z,u,v; } Projected;

static float edge(float ax,float ay,float bx,float by,float x,float y) {
    return (bx-ax)*(y-ay)-(by-ay)*(x-ax);
}
static unsigned texel(float u,unsigned length) {
    if (u<=0) return 0;
    if (u>=1) return length-1;
    unsigned index=(unsigned)(u*(float)(length-1)+.5f);
    return index<length?index:length-1;
}
static Projected project(const FojTexturedVertex *v,
                         const FojTextureCamera *c,
                         float cy,float sy,float cp,float sp,
                         float scale,unsigned w,unsigned h) {
    float x=v->x-c->center_x, y=v->y-c->center_y, z=v->z-c->center_z;
    float horizontal=cy*x+sy*z, rz=-sy*x+cy*z;
    float vertical=cp*y-sp*rz;
    Projected p={
        .x=w*.5f+horizontal*scale,
        .y=h*.5f-vertical*scale,
        .z=sp*y+cp*rz,
        .u=v->u,.v=c->flip_v?1.f-v->v:v->v
    };
    return p;
}
FojTextureStatus foj_textured_render(
    const FojTexturedVertex *vertices,size_t count,
    const FojTexture *tex,const FojRenderSurface *target,
    const FojTextureCamera *cam,size_t *drawn) {
    if (!vertices||!tex||!target||!cam||!drawn||
        !tex->rgba||!target->rgba||!target->depth)
        return FOJ_TEX_ARGUMENT;
    *drawn=0;
    if (!count||count%3||count>20000||
        !tex->width||!tex->height||tex->width>4096||tex->height>4096||
        tex->stride<tex->width||
        !target->width||!target->height||
        target->width>2048||target->height>2048||
        target->color_stride<target->width||
        target->depth_stride<target->width)
        return FOJ_TEX_BOUNDS;
    if (!isfinite(cam->extent)||cam->extent<=0||
        !isfinite(cam->yaw)||!isfinite(cam->pitch)||
        !isfinite(cam->zoom)||cam->zoom<.05f||cam->zoom>8.f||
        !isfinite(cam->center_x)||!isfinite(cam->center_y)||
        !isfinite(cam->center_z))
        return FOJ_TEX_GEOMETRY;

    /* Fail closed before touching a caller-provided framebuffer. */
    for (size_t i=0;i<count;++i) {
        const FojTexturedVertex *v=&vertices[i];
        if (!isfinite(v->x)||!isfinite(v->y)||!isfinite(v->z)||
            !isfinite(v->u)||!isfinite(v->v)||
            fabsf(v->x)>1.e6f||fabsf(v->y)>1.e6f||
            fabsf(v->z)>1.e6f||fabsf(v->u)>1.e6f||
            fabsf(v->v)>1.e6f) return FOJ_TEX_GEOMETRY;
    }
    for (unsigned y=0;y<target->height;++y) {
        uint32_t *rgba=target->rgba+(size_t)y*target->color_stride;
        float *z=target->depth+(size_t)y*target->depth_stride;
        for (unsigned x=0;x<target->width;++x) {
            rgba[x]=UINT32_C(0xff252735);
            z[x]=-INFINITY;
        }
    }
    float cy=cosf(cam->yaw),sy=sinf(cam->yaw);
    float cp=cosf(cam->pitch),sp=sinf(cam->pitch);
    float minimum=target->width<target->height?
        (float)target->width:(float)target->height;
    float scale=.84f*minimum/cam->extent*cam->zoom;
    if (!isfinite(scale)) return FOJ_TEX_GEOMETRY;

    for (size_t i=0;i<count;i+=3) {
        Projected a=project(&vertices[i],cam,cy,sy,cp,sp,
                            scale,target->width,target->height);
        Projected b=project(&vertices[i+1],cam,cy,sy,cp,sp,
                            scale,target->width,target->height);
        Projected c=project(&vertices[i+2],cam,cy,sy,cp,sp,
                            scale,target->width,target->height);
        if (!isfinite(a.x)||!isfinite(a.y)||!isfinite(a.z)||
            !isfinite(b.x)||!isfinite(b.y)||!isfinite(b.z)||
            !isfinite(c.x)||!isfinite(c.y)||!isfinite(c.z)) continue;
        float area=edge(a.x,a.y,b.x,b.y,c.x,c.y);
        if (!isfinite(area)||fabsf(area)<1.e-5f) continue;
        float left=fminf(a.x,fminf(b.x,c.x));
        float right=fmaxf(a.x,fmaxf(b.x,c.x));
        float top=fminf(a.y,fminf(b.y,c.y));
        float bottom=fmaxf(a.y,fmaxf(b.y,c.y));
        if (right<0||bottom<0||left>target->width-1||
            top>target->height-1) continue;
        if (left<0)left=0;
        if (top<0)top=0;
        if (right>target->width-1)right=(float)(target->width-1);
        if (bottom>target->height-1)bottom=(float)(target->height-1);
        int x0=(int)floorf(left),x1=(int)ceilf(right);
        int y0=(int)floorf(top),y1=(int)ceilf(bottom);
        for (int y=y0;y<=y1;++y) {
            uint32_t *rgba=target->rgba+(size_t)y*target->color_stride;
            float *zbuf=target->depth+(size_t)y*target->depth_stride;
            for (int x=x0;x<=x1;++x) {
                float px=(float)x+.5f,py=(float)y+.5f;
                float w0=edge(b.x,b.y,c.x,c.y,px,py)/area;
                float w1=edge(c.x,c.y,a.x,a.y,px,py)/area;
                float w2=1.f-w0-w1;
                if (w0< -1.e-6f||w1< -1.e-6f||w2< -1.e-6f)continue;
                float z=w0*a.z+w1*b.z+w2*c.z;
                if (z<=zbuf[x])continue;
                float u=w0*a.u+w1*b.u+w2*c.u;
                float v=w0*a.v+w1*b.v+w2*c.v;
                unsigned tx=texel(u,tex->width),ty=texel(v,tex->height);
                uint32_t pixel=tex->rgba[(size_t)ty*tex->stride+tx];
                if ((pixel>>24)<128u)continue;
                rgba[x]=pixel|UINT32_C(0xff000000);
                zbuf[x]=z;
                ++*drawn;
            }
        }
    }
    return FOJ_TEX_OK;
}
