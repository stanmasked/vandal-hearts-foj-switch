#include "gpu_vertex_stream.h"
#include <math.h>
#include <stdint.h>

static int good(float x) {
    return isfinite(x) && fabsf(x)<=1000000.0f;
}
FojGpuStreamStatus foj_gpu_prepare_stream(
    const FojTexturedVertex *input,size_t vertex_count,
    const FojTextureSection *sections,size_t section_count,
    size_t texture_count,const FojTextureCamera *camera,
    unsigned width,unsigned height,
    FojGpuVertex *vertices_out,size_t vertex_capacity,
    FojGpuBatch *batches_out,size_t batch_capacity,
    FojGpuStreamInfo *result) {
    if (!input||!sections||!camera||!vertices_out||!batches_out||!result)
        return FOJ_GPU_STREAM_ARGUMENT;
    if (!vertex_count||vertex_count%3||vertex_count>FOJ_GPU_MAX_VERTICES||
        !section_count||section_count>FOJ_GPU_MAX_BATCHES||
        !texture_count||texture_count>FOJ_GPU_MAX_TEXTURES||
        vertex_capacity<vertex_count||batch_capacity<section_count||
        !width||!height||width>2048||height>2048)
        return FOJ_GPU_STREAM_BOUNDS;
    if (!good(camera->center_x)||!good(camera->center_y)||
        !good(camera->center_z)||!good(camera->yaw)||
        !good(camera->pitch)||!good(camera->extent)||
        camera->extent<=0.0f||!good(camera->zoom)||
        camera->zoom<.05f||camera->zoom>8.0f||
        (camera->flip_v!=0&&camera->flip_v!=1))
        return FOJ_GPU_STREAM_INVALID;

    /* No output is changed unless every section, input and projection
       has already passed full validation. */
    size_t covered=0;
    for (size_t s=0;s<section_count;++s) {
        const FojTextureSection *sec=&sections[s];
        if (sec->first_vertex!=covered||!sec->vertex_count||
            sec->vertex_count%3||sec->vertex_count>vertex_count-covered||
            sec->texture_index>=texture_count)
            return FOJ_GPU_STREAM_INVALID;
        covered+=sec->vertex_count;
    }
    if (covered!=vertex_count)return FOJ_GPU_STREAM_INVALID;
    for (size_t i=0;i<vertex_count;++i) {
        const FojTexturedVertex *v=&input[i];
        if (!good(v->x)||!good(v->y)||!good(v->z)||
            !good(v->u)||!good(v->v))return FOJ_GPU_STREAM_INVALID;
    }
    const float cy=cosf(camera->yaw),sy=sinf(camera->yaw);
    const float cp=cosf(camera->pitch),sp=sinf(camera->pitch);
    const float min_side=width<height?(float)width:(float)height;
    const float scale=.84f*min_side/camera->extent*camera->zoom;
    const float nx=2.0f*scale/(float)width;
    const float ny=2.0f*scale/(float)height;
    if (!isfinite(nx)||!isfinite(ny))return FOJ_GPU_STREAM_INVALID;
    for (size_t i=0;i<vertex_count;++i) {
        const FojTexturedVertex *v=&input[i];
        const float x=v->x-camera->center_x;
        const float y=v->y-camera->center_y;
        const float z=v->z-camera->center_z;
        const float rx=cy*x+sy*z,rz=-sy*x+cy*z;
        const float ry=cp*y-sp*rz;
        const float rz_camera=sp*y+cp*rz;
        if (!isfinite(rx*nx)||!isfinite(ry*ny)||
            !isfinite(rz_camera/camera->extent))
            return FOJ_GPU_STREAM_INVALID;
    }
    for (size_t s=0;s<section_count;++s) {
        batches_out[s].first_vertex=(uint32_t)sections[s].first_vertex;
        batches_out[s].vertex_count=(uint32_t)sections[s].vertex_count;
        batches_out[s].texture_index=(uint32_t)sections[s].texture_index;
    }
    for (size_t i=0;i<vertex_count;++i) {
        const FojTexturedVertex *v=&input[i];
        const float x=v->x-camera->center_x;
        const float y=v->y-camera->center_y;
        const float z=v->z-camera->center_z;
        const float rx=cy*x+sy*z,rz=-sy*x+cy*z;
        const float ry=cp*y-sp*rz;
        const float rz_camera=sp*y+cp*rz;
        vertices_out[i]=(FojGpuVertex){
            rx*nx,ry*ny,rz_camera/camera->extent,1.0f,
            v->u,camera->flip_v?1.0f-v->v:v->v
        };
    }
    result->vertices_written=vertex_count;
    result->batches_written=section_count;
    return FOJ_GPU_STREAM_OK;
}
