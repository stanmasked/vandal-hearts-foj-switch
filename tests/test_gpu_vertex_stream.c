/* Generated geometry only. Real PS3 meshes stay user-local. */
#include "gpu_vertex_stream.h"
#include <assert.h>
#include <math.h>
#include <stdio.h>

static int near(float a,float b){return fabsf(a-b)<.0001f;}
static void test_two_material_batches(void) {
    const FojTexturedVertex v[6]={
        {-1,-1,1,0,0},{1,-1,1,1,0},{0,1,1,.5f,1},
        {-1,-1,0,0,0},{1,-1,0,1,0},{0,1,0,.5f,1}
    };
    const FojTextureSection s[2]={{0,3,0},{3,3,1}};
    FojTextureCamera cam={0,0,0,2,0,0,1,0};
    FojGpuVertex out[6]={0};FojGpuBatch batches[2]={0};
    FojGpuStreamInfo info={0};
    assert(foj_gpu_prepare_stream(v,6,s,2,2,&cam,1280,720,
           out,6,batches,2,&info)==FOJ_GPU_STREAM_OK);
    assert(info.vertices_written==6&&info.batches_written==2);
    assert(batches[0].texture_index==0&&batches[1].texture_index==1);
    assert(batches[1].first_vertex==3&&batches[1].vertex_count==3);
    assert(near(out[0].x,-.4725f)&&near(out[0].y,-.84f));
    assert(near(out[0].z,.5f)&&near(out[3].z,0));
    assert(near(out[2].u,.5f)&&near(out[2].v,1.f));
    assert(out[0].w==1.f);
    cam.flip_v=1;
    assert(foj_gpu_prepare_stream(v,6,s,2,2,&cam,1280,720,
           out,6,batches,2,&info)==FOJ_GPU_STREAM_OK);
    assert(near(out[2].v,0)&&near(out[0].v,1));
}
static void test_validation_is_transactional(void) {
    FojTexturedVertex v[3]={{0,0,0,0,0},{1,0,0,1,0},{0,1,0,0,1}};
    FojTextureSection section={0,3,0};
    FojTextureCamera cam={0,0,0,2,0,0,1,0};
    FojGpuVertex output[3]={{9,0,0,0,0,0}};
    FojGpuBatch batch={0};FojGpuStreamInfo info={17,19};
    v[2].u=NAN;
    assert(foj_gpu_prepare_stream(v,3,&section,1,1,&cam,1280,720,
           output,3,&batch,1,&info)==FOJ_GPU_STREAM_INVALID);
    assert(output[0].x==9&&info.vertices_written==17);
    v[2].u=0;section.texture_index=2;
    assert(foj_gpu_prepare_stream(v,3,&section,1,1,&cam,1280,720,
           output,3,&batch,1,&info)==FOJ_GPU_STREAM_INVALID);
    assert(output[0].x==9);
    section.texture_index=0;
    assert(foj_gpu_prepare_stream(v,3,&section,1,1,&cam,1280,720,
           output,2,&batch,1,&info)==FOJ_GPU_STREAM_BOUNDS);
    cam.extent=0;
    assert(foj_gpu_prepare_stream(v,3,&section,1,1,&cam,1280,720,
           output,3,&batch,1,&info)==FOJ_GPU_STREAM_INVALID);
}
int main(void) {
    test_two_material_batches();
    test_validation_is_transactional();
    puts("GPU staging: 2-material clip-space and fail-closed tests passed");
    return 0;
}
