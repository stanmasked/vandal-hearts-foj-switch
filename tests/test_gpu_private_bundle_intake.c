#define _POSIX_C_SOURCE 200809L
#ifdef NDEBUG
#undef NDEBUG
#endif
#include "private_bundle_intake.h"
#include <assert.h>
#include <errno.h>
#include <math.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <sys/stat.h>
#include <unistd.h>

enum { MESH_BYTES=28+32+2*8+6*76, MAT_BYTES=24,
       DDS_BYTES=128+8*8*4 };
static void u32(uint8_t *p,uint32_t v) {
    for(unsigned i=0;i<4;++i)p[i]=(uint8_t)(v>>(8u*i));
}
static void f32(uint8_t *p,float f) {
    uint32_t b;memcpy(&b,&f,4);u32(p,b);
}
static void gen_mesh(uint8_t b[MESH_BYTES]) {
    memset(b,0,MESH_BYTES);
    memcpy(b,"FOJRM001",8);
    u32(b+8,1);u32(b+12,1);u32(b+16,6);u32(b+20,2);
    u32(b+28,UINT32_MAX);f32(b+44,1.f);
    u32(b+60,0);u32(b+64,3);u32(b+68,3);u32(b+72,3);
    size_t p=76;
    for(unsigned i=0;i<6;++i,p+=76) {
        f32(b+p,(float)(i%3)-1.f);
        f32(b+p+4,(float)(i/3));
        f32(b+p+8,(float)(i/3));
        f32(b+p+12,(float)(i%3)/2.f);
        f32(b+p+16,(float)(i/3));
        f32(b+p+28,1.f);
        u32(b+p+32,1);
        u32(b+p+36,0);
        f32(b+p+40,1.f);
    }
    assert(p==MESH_BYTES);
}
static void gen_material(uint8_t b[MAT_BYTES]) {
    memset(b,0,MAT_BYTES);memcpy(b,"FOJMAT01",8);
    u32(b+8,2);u32(b+12,2);u32(b+16,0);u32(b+20,1);
}
static void gen_dds(uint8_t b[DDS_BYTES],unsigned color) {
    memset(b,0,DDS_BYTES);memcpy(b,"DDS ",4);
    u32(b+4,124);u32(b+8,0x100f);
    u32(b+12,8);u32(b+16,8);u32(b+20,32);
    u32(b+76,32);u32(b+80,0x41);u32(b+88,32);
    u32(b+92,0xff);u32(b+96,0xff00);
    u32(b+100,0xff0000);u32(b+104,0xff000000);
    u32(b+108,0x1000);
    for(size_t i=128;i<DDS_BYTES;i+=4) {
        b[i]=(uint8_t)color;
        b[i+1]=50;b[i+2]=90;b[i+3]=255;
    }
}
static void save(const char *path,const void *data,size_t len) {
    FILE *f=fopen(path,"wb");assert(f);
    assert(fwrite(data,1,len,f)==len);
    assert(fclose(f)==0);
}
static FojTextureCamera camera(void) {
    FojTextureCamera c={0,0,0,2,0,0,1,0};return c;
}
static FojGpuPrivateBundleStatus run(
    const char *mesh,const char *mat,const char *dds0,const char *dds1,
    FojGpuPrivateBundleReport *out) {
    const char *names[2]={dds0,dds1};
    FojTextureCamera cam=camera();
    return foj_gpu_private_bundle_preflight(
        mesh,mat,names,&cam,1280,720,4096,out);
}
static void rejected(const char *mesh,const char *mat,
    const char *dds0,const char *dds1,FojGpuPrivateBundleStatus expected) {
    FojGpuPrivateBundleReport report,original;
    memset(&report,0xA5,sizeof(report));original=report;
    assert(run(mesh,mat,dds0,dds1,&report)==expected);
    assert(memcmp(&report,&original,sizeof(report))==0);
}
int main(void) {
    const char *mesh="build/stage258-actor.fojrm";
    const char *mat="build/stage258-actor.fojmat";
    const char *dds0="build/stage258-material0.dds";
    const char *dds1="build/stage258-material1.dds";
    const char *link="build/stage258-link.fojrm";
    const char *dir="build/stage258-dir.fojmat";
    const char *absent="build/stage258-absent.dds";
    if (mkdir("build",0700)) assert(errno==EEXIST);
    uint8_t m[MESH_BYTES],t[MAT_BYTES],a[DDS_BYTES],b[DDS_BYTES];
    gen_mesh(m);gen_material(t);gen_dds(a,45);gen_dds(b,215);
    save(mesh,m,sizeof(m));save(mat,t,sizeof(t));
    save(dds0,a,sizeof(a));save(dds1,b,sizeof(b));
    FojGpuPrivateBundleReport report={0};
    assert(run(mesh,mat,dds0,dds1,&report)==FOJ_PRIVATE_BUNDLE_OK);
    assert(report.actor.stream.vertices_written==6);
    assert(report.actor.stream.batches_written==2);
    assert(report.actor.upload.allocation_bytes==4096);
    assert(report.actor.upload.material_mask==3);
    assert(report.atlas_count==2);
    for(unsigned i=0;i<2;++i) {
        assert(report.atlas[i].width==8);
        assert(report.atlas[i].height==8);
        assert(report.atlas[i].pixel_bytes==256);
    }
    rejected(mesh,mat,dds0,absent,FOJ_PRIVATE_BUNDLE_MISSING);
    rejected(absent,mat,dds0,dds1,FOJ_PRIVATE_BUNDLE_MISSING);
    assert(symlink("stage258-actor.fojrm",link)==0);
    rejected(link,mat,dds0,dds1,FOJ_PRIVATE_BUNDLE_PATH_REJECTED);
    assert(unlink(link)==0);
    assert(mkdir(dir,0700)==0);
    rejected(mesh,dir,dds0,dds1,FOJ_PRIVATE_BUNDLE_PATH_REJECTED);
    assert(rmdir(dir)==0);
    save(dds1,b,130);
    rejected(mesh,mat,dds0,dds1,FOJ_PRIVATE_BUNDLE_INVALID);
    save(dds1,b,sizeof(b));
    b[0]='x';save(dds1,b,sizeof(b));
    rejected(mesh,mat,dds0,dds1,FOJ_PRIVATE_BUNDLE_INVALID);
    gen_dds(b,215);save(dds1,b,sizeof(b));
    t[20]=2;save(mat,t,sizeof(t));
    rejected(mesh,mat,dds0,dds1,FOJ_PRIVATE_BUNDLE_INVALID);
    gen_material(t);u32(t+12,1);save(mat,t,sizeof(t));
    rejected(mesh,mat,dds0,dds1,FOJ_PRIVATE_BUNDLE_INVALID);
    gen_material(t);save(mat,t,sizeof(t));
    m[0]='X';save(mesh,m,sizeof(m));
    rejected(mesh,mat,dds0,dds1,FOJ_PRIVATE_BUNDLE_INVALID);
    gen_mesh(m);save(mesh,m,sizeof(m));
    save(mesh,m,sizeof(m)-1);
    rejected(mesh,mat,dds0,dds1,FOJ_PRIVATE_BUNDLE_INVALID);
    save(mesh,m,sizeof(m));
    rejected(mesh,mat,dds0,NULL,FOJ_PRIVATE_BUNDLE_ARGUMENT);
    assert(strcmp(foj_gpu_private_bundle_status_name(
                    FOJ_PRIVATE_BUNDLE_MISSING),
                  "required private part missing")==0);
    assert(remove(mesh)==0);assert(remove(mat)==0);
    assert(remove(dds0)==0);assert(remove(dds1)==0);
    puts("Stage258 bounded two-atlas private bundle intake: PASS");
    return 0;
}
