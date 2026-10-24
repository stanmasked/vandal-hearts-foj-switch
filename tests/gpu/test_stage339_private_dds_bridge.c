#include "stage339_private_dds_bridge.h"
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

static void put32(uint8_t *p,uint32_t x) {
    p[0]=(uint8_t)x; p[1]=(uint8_t)(x>>8);
    p[2]=(uint8_t)(x>>16); p[3]=(uint8_t)(x>>24);
}
static size_t make_dds(uint8_t *d,size_t cap,FojStage332Format format) {
    const int compressed=(format==FOJ_STAGE332_BC1 ||
                          format==FOJ_STAGE332_BC2);
    const uint32_t w=compressed?5u:3u,h=compressed?3u:2u;
    const uint32_t payload=compressed?
        (format==FOJ_STAGE332_BC1?16u:32u):
        w*h*(format==FOJ_STAGE332_BGRA8?4u:3u);
    const size_t n=128u+payload;
    assert(cap>=n);
    memset(d,0,n);
    memcpy(d,"DDS ",4);
    put32(d+4,124u);
    put32(d+8,compressed?0x81007u:0x100fu);
    put32(d+12,h);put32(d+16,w);put32(d+20,
         compressed?payload:w*(format==FOJ_STAGE332_BGRA8?4u:3u));
    put32(d+76,32u); put32(d+80,compressed?4u:
                                format==FOJ_STAGE332_BGRA8?0x41u:0x40u);
    put32(d+84,format==FOJ_STAGE332_BC1?0x31545844u:
                 format==FOJ_STAGE332_BC2?0x33545844u:0);
    if(!compressed) {
        put32(d+88,format==FOJ_STAGE332_BGRA8?32u:24u);
        put32(d+92,0x00ff0000u);
        put32(d+96,0x0000ff00u);
        put32(d+100,0x000000ffu);
        put32(d+104,format==FOJ_STAGE332_BGRA8?0xff000000u:0u);
    }
    put32(d+108,0x1000u);
    if(format==FOJ_STAGE332_BGRA8) {
        for(unsigned i=0;i<6u;++i) {
            d[128u+4u*i]=20; d[129u+4u*i]=60;
            d[130u+4u*i]=90; d[131u+4u*i]=140;
        }
    } else if(format==FOJ_STAGE332_BGR8) {
        for(unsigned i=0;i<6u;++i) {
            d[128u+3u*i]=9; d[129u+3u*i]=25; d[130u+3u*i]=71;
        }
    } else {
        /* Invented DXT endpoints; never copied from any game. */
        const size_t block= format==FOJ_STAGE332_BC1?8u:16u;
        for(size_t i=0;i<payload;i+=block) {
            uint8_t *p=d+128u+i+(format==FOJ_STAGE332_BC2?8u:0u);
            p[0]=0x00; p[1]=0xf8; p[2]=0x1f; p[3]=0x00;
        }
        if(format==FOJ_STAGE332_BC2) {
            for(size_t i=0;i<payload;i+=16u)
                memset(d+128u+i,0xff,8u);
        }
    }
    return n;
}
static void expect_refusal(const uint8_t *d,size_t n,
                           size_t capacity,uint32_t row_alignment,
                           uint64_t image_size,uint32_t image_alignment) {
    uint8_t out[128]; memset(out,0xA5,sizeof(out));
    FojStage339Prepared result;
    memset(&result,0xD1,sizeof(result));
    FojStage339Prepared backup; memcpy(&backup,&result,sizeof(backup));
    assert(!foj_stage339_prepare_private_dds(
        d,n,out,capacity,row_alignment,image_size,image_alignment,&result));
    for(size_t i=0;i<sizeof(out);++i)assert(out[i]==0xA5u);
    assert(!memcmp(&result,&backup,sizeof(result)));
}
static void verify_format(FojStage332Format fmt) {
    uint8_t d[256],out[128];
    size_t len=make_dds(d,sizeof(d),fmt);
    memset(out,0xA5,sizeof(out));
    FojStage339Prepared p={0};
    assert(foj_stage339_prepare_private_dds(
         d,len,out,sizeof(out),64u,65536u,4096u,&p));
    assert(p.image.format==fmt);
    assert(p.image.width==(fmt>=FOJ_STAGE332_BC1?5u:3u));
    assert(p.image.height==(fmt>=FOJ_STAGE332_BC1?3u:2u));
    assert(p.image.mip_levels==1u);
    assert(p.gpu.rows.row_pitch_bytes==64u);
    assert(p.gpu.rows.row_length_pixels==16u);
    assert(p.gpu.staging_allocation_bytes==4096u);
    assert(p.gpu.image_allocation_bytes==65536u);
    if(fmt==FOJ_STAGE332_BGRA8) {
        for(unsigned i=0;i<6u;++i)
            assert(out[4u*i]==90 && out[4u*i+1u]==60 &&
                   out[4u*i+2u]==20 && out[4u*i+3u]==140);
    }
    if(fmt==FOJ_STAGE332_BGR8)
        for(unsigned i=0;i<6u;++i)
            assert(out[4u*i]==71 && out[4u*i+1u]==25 &&
                   out[4u*i+2u]==9 && out[4u*i+3u]==255);
    if(fmt==FOJ_STAGE332_BC1 || fmt==FOJ_STAGE332_BC2) {
        assert(out[0]==255 && out[1]==0 && out[2]==0);
        assert(out[3]==255);
    }
    const size_t rgba=p.image.rgba_bytes;
    for(size_t i=rgba;i<sizeof(out);++i)assert(out[i]==0xA5u);
    expect_refusal(d,len,rgba-1u,64u,65536u,4096u);
    expect_refusal(d,len,rgba,1u,65536u,4096u);
    expect_refusal(d,len,rgba,64u,UINT64_MAX,4096u);
    expect_refusal(d,len,rgba,64u,65536u,3u);
    expect_refusal(d,len-1u,rgba,64u,65536u,4096u);
    d[len]=0x91;
    expect_refusal(d,len+1u,rgba,64u,65536u,4096u);
    put32(d+8,0u); /* corrupt exact-format header flags */
    expect_refusal(d,len,rgba,64u,65536u,4096u);
    put32(d+8,(fmt>=FOJ_STAGE332_BC1?0x81007u:0x100fu));
    /* Explicitly test overlapping input and output refusal, no mutation. */
    FojStage339Prepared unchanged; memset(&unchanged,0xD1,sizeof(unchanged));
    FojStage339Prepared backup=unchanged;
    assert(!foj_stage339_prepare_private_dds(
        d,len,d+8,rgba,64u,65536u,4096u,&unchanged));
    assert(!memcmp(&backup,&unchanged,sizeof(unchanged)));
}
int main(void) {
    verify_format(FOJ_STAGE332_BGRA8);
    verify_format(FOJ_STAGE332_BGR8);
    verify_format(FOJ_STAGE332_BC1);
    verify_format(FOJ_STAGE332_BC2);
    puts("STAGE339_SYNTHETIC_OWNER_DDS_DECODE_GPU_PLAN_FAIL_CLOSED_PASS");
    return 0;
}
