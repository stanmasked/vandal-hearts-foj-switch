/* Stage257 entirely GENERATED files: no original FoJ mesh or DDS bytes.
 * Tests the real private-container parsers and GPU stream/upload planners. */
#ifdef NDEBUG
#undef NDEBUG
#endif
#include <assert.h>
#include <math.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include "private_actor_bridge.h"

enum { MESH_BYTES=28+32+2*8+6*76, MATERIAL_BYTES=16+2*4 };
static void write32(uint8_t *p,uint32_t n) {
    for(unsigned j=0;j<4;++j)p[j]=(uint8_t)(n>>(8u*j));
}
static void writef(uint8_t *p,float v) {
    uint32_t b;
    memcpy(&b,&v,sizeof(b));
    write32(p,b);
}

static void make_mesh(uint8_t m[MESH_BYTES]) {
    memset(m,0,MESH_BYTES);
    memcpy(m,"FOJRM001",8);
    write32(m+8,1);
    write32(m+12,1); /* one synthetic root bone */
    write32(m+16,6); /* two triangles, two material sections */
    write32(m+20,2);
    write32(m+28,UINT32_MAX);
    writef(m+28+4+12,1.f); /* identity quaternion W */
    const size_t sec=28+32;
    write32(m+sec,0);
    write32(m+sec+4,3);
    write32(m+sec+8,3);
    write32(m+sec+12,3);
    size_t p=sec+16;
    for(unsigned i=0;i<6;++i) {
        writef(m+p,(float)(i%3)-1.f);
        writef(m+p+4,(float)(i/3));
        writef(m+p+8,(float)(i/3));
        writef(m+p+12,(float)(i%3)/2.f);
        writef(m+p+16,(float)(i/3));
        writef(m+p+28,1.f); /* normal Z */
        write32(m+p+32,1); /* one nonzero bone influence */
        write32(m+p+36,0);
        writef(m+p+40,1.f);
        p+=76;
    }
    assert(p==MESH_BYTES);
}
static void make_material(uint8_t t[MATERIAL_BYTES]) {
    memset(t,0,MATERIAL_BYTES);
    memcpy(t,"FOJMAT01",8);
    write32(t+8,2);
    write32(t+12,2);
    write32(t+16,0);
    write32(t+20,1);
}
static FojTextureCamera camera(void) {
    FojTextureCamera c={0.f,0.f,0.f,2.f,0.f,0.f,1.f,0};
    return c;
}
static FojGpuStreamStatus prepare(
    const uint8_t *m,size_t ml,const uint8_t *t,size_t tl,
    const FojTextureCamera *cam,size_t align,
    FojGpuVertex *vertices,size_t vc,
    FojGpuBatch *batches,size_t bc,FojGpuPrivateActorPlan *p) {
    return foj_gpu_private_actor_prepare(
        m,ml,t,tl,cam,1280,720,align,vertices,vc,batches,bc,p);
}
static void reject_unchanged(
    const uint8_t *m,size_t ml,const uint8_t *t,size_t tl,
    const FojTextureCamera *cam,size_t align,
    size_t vcap,size_t bcap,FojGpuStreamStatus expected) {
    FojGpuVertex v[7],copy_v[7];
    FojGpuBatch b[3],copy_b[3];
    FojGpuPrivateActorPlan plan,copy_plan;
    memset(v,0xB6,sizeof(v));
    memset(b,0xA5,sizeof(b));
    memset(&plan,0x4D,sizeof(plan));
    memcpy(copy_v,v,sizeof(v));
    memcpy(copy_b,b,sizeof(b));
    memcpy(&copy_plan,&plan,sizeof(plan));
    assert(prepare(m,ml,t,tl,cam,align,v,vcap,b,bcap,&plan)==expected);
    assert(memcmp(v,copy_v,sizeof(v))==0);
    assert(memcmp(b,copy_b,sizeof(b))==0);
    assert(memcmp(&plan,&copy_plan,sizeof(plan))==0);
}
int main(void) {
    uint8_t m[MESH_BYTES],t[MATERIAL_BYTES];
    make_mesh(m);
    make_material(t);
    FojTextureCamera cam=camera();
    FojGpuVertex v[7]={0};
    FojGpuBatch b[3]={0};
    FojGpuPrivateActorPlan p={0};
    assert(prepare(m,sizeof(m),t,sizeof(t),&cam,4096,v,6,b,2,&p)==
           FOJ_GPU_STREAM_OK);
    assert(p.stream.vertices_written==6);
    assert(p.stream.batches_written==2);
    assert(p.upload.payload_bytes==144);
    assert(p.upload.allocation_bytes==4096);
    assert(p.upload.material_mask==3);
    assert(p.upload.batch_count==2);
    assert(b[0].first_vertex==0&&b[0].vertex_count==3&&
           b[0].texture_index==0);
    assert(b[1].first_vertex==3&&b[1].vertex_count==3&&
           b[1].texture_index==1);
    assert(fabsf(v[0].u)<1e-6f&&fabsf(v[2].u-1.f)<1e-6f);
    assert(v[0].w==1.f && v[3].z>v[0].z);
    assert(v[6].w==0.f); /* canary beyond exact capacity */
    assert(b[2].vertex_count==0);

    reject_unchanged(m,sizeof(m)-1,t,sizeof(t),&cam,4096,6,2,
                     FOJ_GPU_STREAM_INVALID);
    reject_unchanged(m,sizeof(m),t,sizeof(t)-1,&cam,4096,6,2,
                     FOJ_GPU_STREAM_INVALID);
    reject_unchanged(m,sizeof(m),t,sizeof(t),&cam,4096,5,2,
                     FOJ_GPU_STREAM_BOUNDS);
    reject_unchanged(m,sizeof(m),t,sizeof(t),&cam,4096,6,1,
                     FOJ_GPU_STREAM_BOUNDS);
    reject_unchanged(m,sizeof(m),t,sizeof(t),&cam,24,6,2,
                     FOJ_GPU_STREAM_BOUNDS);
    cam.extent=0;
    reject_unchanged(m,sizeof(m),t,sizeof(t),&cam,4096,6,2,
                     FOJ_GPU_STREAM_INVALID);
    cam=camera();
    t[0]='X';
    reject_unchanged(m,sizeof(m),t,sizeof(t),&cam,4096,6,2,
                     FOJ_GPU_STREAM_INVALID);
    make_material(t);
    write32(t+20,2);
    reject_unchanged(m,sizeof(m),t,sizeof(t),&cam,4096,6,2,
                     FOJ_GPU_STREAM_INVALID);
    make_material(t);
    write32(t+8,1);
    reject_unchanged(m,sizeof(m),t,20,&cam,4096,6,2,
                     FOJ_GPU_STREAM_BOUNDS);
    make_material(t);
    m[0]='X';
    reject_unchanged(m,sizeof(m),t,sizeof(t),&cam,4096,6,2,
                     FOJ_GPU_STREAM_INVALID);
    make_mesh(m);
    write32(m+28+32+8,4);
    reject_unchanged(m,sizeof(m),t,sizeof(t),&cam,4096,6,2,
                     FOJ_GPU_STREAM_INVALID);
    make_mesh(m);
    writef(m+28+32+16+12,NAN); /* bad UV */
    reject_unchanged(m,sizeof(m),t,sizeof(t),&cam,4096,6,2,
                     FOJ_GPU_STREAM_INVALID);
    make_mesh(m);
    reject_unchanged(m,FOJ_RIGMESH_MAX_FILE_BYTES+1,t,sizeof(t),&cam,
                     4096,6,2,FOJ_GPU_STREAM_BOUNDS);
    reject_unchanged(NULL,sizeof(m),t,sizeof(t),&cam,4096,6,2,
                     FOJ_GPU_STREAM_ARGUMENT);
    puts("Stage257 generated private actor FOJRM/FOJMAT to GPU bridge: PASS");
    return 0;
}
