/* Generated-only BANIM test clip. No original PS3 game data in CI. */
#include "banim_core.h"

#include <assert.h>
#include <math.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

static void u16(uint8_t *p, unsigned value) {
    p[0]=(uint8_t)value;p[1]=(uint8_t)(value>>8);
}
static void u32(uint8_t *p,uint32_t v) {
    p[0]=(uint8_t)v;p[1]=(uint8_t)(v>>8);
    p[2]=(uint8_t)(v>>16);p[3]=(uint8_t)(v>>24);
}
static void f32(uint8_t *p,float value) {
    uint32_t bits;
    memcpy(&bits,&value,sizeof(bits));
    u32(p,bits);
}
static size_t emit_track(uint8_t *b,size_t pos,unsigned parent,
                         const float (*keys)[8],unsigned n) {
    b[pos]=0x11;
    u16(b+pos+1,parent);
    u16(b+pos+3,n);
    pos+=5;
    for (unsigned k=0;k<n;++k) {
        b[pos++]=0x12;
        for (int v=0;v<8;++v) {
            f32(b+pos,keys[k][v]);
            pos+=4;
        }
    }
    return pos;
}

static size_t build_clip(uint8_t *b) {
    static const float root[][8] = {
        {0,0,0,0,1,0,0,0},
        {1,0,0,1,0,2,0,0}
    };
    static const float child[][8] = {{0.5f,0,0,0,1,0,1,0}};
    size_t pos=0;
    b[pos++]=0x0d; f32(b+pos,1);pos+=4;
    u32(b+pos,2);pos+=4;
    u16(b+pos,0);pos+=2;
    pos=emit_track(b,pos,0xffff,root,2);
    pos=emit_track(b,pos,0,child,1);
    b[pos++]=0x13;
    return pos;
}

static void test_parse_and_sample(void) {
    uint8_t data[160]={0};
    size_t size=build_clip(data);
    assert(size==11+5+2*33+5+33+1);
    FojAnimClip clip={0};
    assert(foj_banim_parse(data,size,&clip)==FOJ_ANIM_OK);
    assert(clip.duration==1.f && clip.track_count==2);
    assert(clip.tracks[0].parent==-1 && clip.tracks[1].parent==0);
    assert(clip.tracks[0].count==2 && clip.tracks[1].count==1);
    FojLocalPose sampled[2]={0};
    assert(foj_banim_sample(&clip,0.5f,sampled,2)==FOJ_ANIM_OK);
    assert(fabsf(sampled[0].quat_xyzw[2]-0.7071068f)<0.001f);
    assert(fabsf(sampled[0].quat_xyzw[3]-0.7071068f)<0.001f);
    assert(fabsf(sampled[0].translation_xyz[0]-1.f)<0.001f);
    assert(sampled[1].translation_xyz[1]==1.f);
    assert(foj_banim_sample(&clip,-2,sampled,2)==FOJ_ANIM_OK);
    assert(sampled[0].translation_xyz[0]==0.f);
    assert(foj_banim_sample(&clip,20,sampled,2)==FOJ_ANIM_OK);
    assert(sampled[0].translation_xyz[0]==2.f);
    assert(foj_banim_sample(&clip,0,sampled,1)==FOJ_ANIM_CAPACITY);
    foj_banim_free(&clip);
    assert(clip.tracks==NULL && clip.track_count==0);
}

static void test_corrupt_and_short(void) {
    uint8_t data[160]={0};
    size_t length=build_clip(data);
    FojAnimClip clip={0};
    assert(foj_banim_parse(data,length-1,&clip)==FOJ_ANIM_FORMAT);
    assert(clip.tracks==NULL);
    data[11]=0xaa;
    assert(foj_banim_parse(data,length,&clip)==FOJ_ANIM_FORMAT);
    assert(clip.tracks==NULL);
    data[11]=0x11;
    u16(data+12,3);
    assert(foj_banim_parse(data,length,&clip)==FOJ_ANIM_FORMAT);
    u16(data+12,0xffff);
    data[16]=0xab;
    assert(foj_banim_parse(data,length,&clip)==FOJ_ANIM_FORMAT);
    data[16]=0x12;
    f32(data+17,INFINITY);
    assert(foj_banim_parse(data,length,&clip)==FOJ_ANIM_FORMAT);
    assert(clip.tracks==NULL);
}

static void test_single_frame_zero_duration(void) {
    uint8_t data[50]={0};
    data[0]=0x0d;f32(data+1,0);u32(data+5,1);
    data[11]=0x11;u16(data+12,0xffff);u16(data+14,1);
    data[16]=0x12;f32(data+17,0);
    f32(data+21,0);f32(data+25,0);f32(data+29,0);
    f32(data+33,1);f32(data+37,0);f32(data+41,0);f32(data+45,0);
    data[49]=0x13;
    FojAnimClip clip={0};
    assert(foj_banim_parse(data,sizeof(data),&clip)==FOJ_ANIM_OK);
    assert(clip.track_count==1 && clip.tracks[0].count==1);
    foj_banim_free(&clip);
}

int main(void) {
    test_parse_and_sample();
    test_corrupt_and_short();
    test_single_frame_zero_duration();
    puts("BANIM native C reader and quaternion pose sampler tests passed");
    return 0;
}
