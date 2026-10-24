/* Generated FOJRM001 fixture; no copyrighted mesh or animation bytes. */
#include "rigmesh_io.h"

#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <math.h>

static void u32(uint8_t *p, uint32_t v) {
    for (int i=0;i<4;++i)p[i]=(uint8_t)(v>>(8*i));
}
static void f32(uint8_t *p, float v) {
    uint32_t bits;
    memcpy(&bits,&v,4);
    u32(p,bits);
}
static void bone(uint8_t *p,uint32_t parent,float tx,float ty) {
    u32(p,parent);
    f32(p+4,0);f32(p+8,0);f32(p+12,0);f32(p+16,1);
    f32(p+20,tx);f32(p+24,ty);f32(p+28,0);
}
static size_t make_mesh(uint8_t *data) {
    memset(data,0,700);
    memcpy(data,"FOJRM001",8);
    u32(data+8,1);u32(data+12,2);u32(data+16,6);
    u32(data+20,2);u32(data+24,0);
    size_t p=28;
    bone(data+p,UINT32_MAX,10,0);p+=32;
    bone(data+p,0,0,2);p+=32;
    u32(data+p,0);u32(data+p+4,3);p+=8;
    u32(data+p,3);u32(data+p+4,3);p+=8;
    for (int i=0;i<6;++i) {
        float x=11.f+(float)(i%3),y=2.f+(float)(i/3);
        f32(data+p,x);f32(data+p+4,y);f32(data+p+8,0);
        f32(data+p+12,(float)(i%3)/2.f);f32(data+p+16,(float)i/6.f);
        f32(data+p+20,0);f32(data+p+24,0);f32(data+p+28,1);
        u32(data+p+32,i==0?2:1);
        p+=36;
        u32(data+p,i==0?0u:1u);f32(data+p+4,i==0?.5f:1.f);p+=8;
        u32(data+p,i==0?1u:0u);f32(data+p+4,i==0?.5f:0.f);p+=8;
        for (int j=2;j<5;++j) {u32(data+p,0);f32(data+p+4,0);p+=8;}
    }
    return p;
}

static size_t make_static_mesh(uint8_t *data) {
    memset(data,0,700);
    memcpy(data,"FOJRM001",8);
    u32(data+8,1);u32(data+12,0);u32(data+16,6);
    u32(data+20,2);u32(data+24,0);
    size_t p=28;
    u32(data+p,0);u32(data+p+4,3);p+=8;
    u32(data+p,3);u32(data+p+4,3);p+=8;
    for (int i=0;i<6;++i) {
        float x=-.8f+(float)(i%3)*.2f,y=-.4f+(float)(i/3)*.8f;
        f32(data+p,x);f32(data+p+4,y);f32(data+p+8,0);
        f32(data+p+12,(float)(i%3)/2.f);f32(data+p+16,(float)i/6.f);
        f32(data+p+20,0);f32(data+p+24,0);f32(data+p+28,1);
        u32(data+p+32,0);
        p+=36;
        for (int j=0;j<5;++j) {u32(data+p,0);f32(data+p+4,0);p+=8;}
    }
    return p;
}

static void test_unskinned_static_mesh_roundtrip(void) {
    uint8_t data[700];
    size_t n=make_static_mesh(data);
    assert(n==28+2*8+6*76);
    FojRigMesh mesh={0};
    assert(foj_rigmesh_parse(data,n,&mesh)==FOJ_RIGMESH_OK);
    assert(mesh.bone_count==0 && mesh.bind_bones==NULL);
    assert(mesh.vertex_count==6 && mesh.section_count==2);
    assert(mesh.sections[0].start_vertex==0 && mesh.sections[0].vertex_count==3);
    assert(mesh.sections[1].start_vertex==3 && mesh.sections[1].vertex_count==3);
    for (size_t i=0;i<mesh.vertex_count;++i)
        assert(mesh.vertices[i].influence_count==0);
    FojAnimTrack track={.parent=-1};
    FojAnimClip clip={.track_count=1,.tracks=&track};
    assert(!foj_rigmesh_clip_matches(&mesh,&clip));
    foj_rigmesh_free(&mesh);
    assert(!mesh.bind_bones && !mesh.vertices && !mesh.attributes && !mesh.sections);

    n=make_static_mesh(data);
    u32(data+28+2*8+32,1); /* static vertex falsely claims one influence */
    u32(data+28+2*8+36,0);f32(data+28+2*8+40,1.f);
    assert(foj_rigmesh_parse(data,n,&mesh)==FOJ_RIGMESH_FORMAT);
    assert(!mesh.bind_bones && !mesh.vertices);
}

static void test_synthetic_rigmesh_roundtrip(void) {
    uint8_t data[700];
    size_t n=make_mesh(data);
    assert(n==28+2*32+2*8+6*76);
    FojRigMesh mesh={0};
    assert(foj_rigmesh_parse(data,n,&mesh)==FOJ_RIGMESH_OK);
    assert(mesh.bone_count==2 && mesh.vertex_count==6);
    assert(mesh.section_count==2);
    assert(mesh.sections[1].start_vertex==3 && mesh.sections[1].vertex_count==3);
    assert(mesh.bind_bones[0].parent==-1 && mesh.bind_bones[1].parent==0);
    assert(mesh.vertices[0].influence_count==2);
    assert(mesh.vertices[0].influences[1].weight==.5f);
    assert(mesh.attributes[2].uv[0]==1.f);
    FojAnimTrack tracks[2]={{.parent=-1},{.parent=0}};
    FojAnimClip clip={.track_count=2,.tracks=tracks};
    assert(foj_rigmesh_clip_matches(&mesh,&clip));
    tracks[1].parent=-1;
    assert(!foj_rigmesh_clip_matches(&mesh,&clip));
    FojBoneTransform pose[2];
    memcpy(pose,mesh.bind_bones,2*sizeof(*pose));
    FojSkinMatrix palette[2];
    assert(foj_skin_build_palette(mesh.bind_bones,pose,2,palette,2)==FOJ_SKIN_OK);
    float xyz[18];
    assert(foj_skin_deform(mesh.vertices,0,palette,2,xyz,18)==FOJ_SKIN_OK);
    /* FojRigVertexAttributes lives beside (not inside) FojSkinnedVertex.
       Native viewer must create a contiguous array of weighted vertices,
       which this loader explicitly provides. */
    assert(foj_skin_deform(mesh.vertices,6,palette,2,xyz,18)==FOJ_SKIN_OK);
    for (int i=0;i<6;++i) {
        assert(fabsf(xyz[3*i]-mesh.vertices[i].xyz[0])<0.001f);
        assert(fabsf(xyz[3*i+1]-mesh.vertices[i].xyz[1])<0.001f);
    }
    foj_rigmesh_free(&mesh);
    assert(!mesh.bind_bones && !mesh.vertices);
}

static void test_header_corruption_rejected_without_leaks(void) {
    uint8_t data[700];
    size_t n=make_mesh(data);
    FojRigMesh mesh={0};
    data[0]='x';
    assert(foj_rigmesh_parse(data,n,&mesh)==FOJ_RIGMESH_FORMAT);
    data[0]='F';
    assert(foj_rigmesh_parse(data,n-1,&mesh)==FOJ_RIGMESH_FORMAT);
    u32(data+20,255);
    assert(foj_rigmesh_parse(data,n,&mesh)==FOJ_RIGMESH_LIMIT);
    u32(data+20,2);
    u32(data+28+2*32+8,4); /* next section not contiguous */
    assert(foj_rigmesh_parse(data,n,&mesh)==FOJ_RIGMESH_FORMAT);
    assert(mesh.bind_bones==NULL);
    u32(data+28+2*32+8,3);
    u32(data+28+32,2); /* second bone parent itself */
    assert(foj_rigmesh_parse(data,n,&mesh)==FOJ_RIGMESH_FORMAT);
    u32(data+28+32,0);
    size_t first=28+2*32+2*8;
    u32(data+first+32,6);
    assert(foj_rigmesh_parse(data,n,&mesh)==FOJ_RIGMESH_FORMAT);
    assert(mesh.vertices==NULL);
    u32(data+first+32,2);
    f32(data+first+36+4,NAN);
    assert(foj_rigmesh_parse(data,n,&mesh)==FOJ_RIGMESH_FORMAT);
}

int main(void) {
    test_synthetic_rigmesh_roundtrip();
    test_unskinned_static_mesh_roundtrip();
    test_header_corruption_rejected_without_leaks();
    puts("FOJRM001 parser: static and rigged sections/bones/weights checked");
    return 0;
}
