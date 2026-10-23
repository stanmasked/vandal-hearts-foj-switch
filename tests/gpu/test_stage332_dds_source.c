#include "stage332_dds_source.h"
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static void put32(uint8_t *p, uint32_t x) {
    p[0] = (uint8_t)x; p[1] = (uint8_t)(x >> 8);
    p[2] = (uint8_t)(x >> 16); p[3] = (uint8_t)(x >> 24);
}
static size_t level_bytes(unsigned w, unsigned h, FojStage332Format fmt) {
    if (fmt == FOJ_STAGE332_BGRA8 || fmt == FOJ_STAGE332_BGR8)
        return (size_t)w * h * (fmt == FOJ_STAGE332_BGRA8 ? 4u : 3u);
    return (size_t)((w + 3u) / 4u) * ((h + 3u) / 4u) *
           (fmt == FOJ_STAGE332_BC1 ? 8u : 16u);
}
static size_t build(uint8_t *buf, size_t cap, FojStage332Format fmt,
                    unsigned w, unsigned h, unsigned mips) {
    const int raw = fmt == FOJ_STAGE332_BGRA8 || fmt == FOJ_STAGE332_BGR8;
    unsigned tw = w, th = h;
    size_t total = 128;
    for (unsigned i = 0; i < mips; ++i) {
        total += level_bytes(tw, th, fmt);
        tw = tw > 1u ? tw / 2u : 1u;
        th = th > 1u ? th / 2u : 1u;
    }
    assert(cap >= total);
    memset(buf, 0, total);
    memcpy(buf, "DDS ", 4);
    put32(buf + 4, 124);
    put32(buf + 8, (raw ? 0x100fu : 0x81007u) | (mips > 1 ? 0x20000u : 0u));
    put32(buf + 12, h); put32(buf + 16, w);
    put32(buf + 20, raw ? w * (fmt == FOJ_STAGE332_BGRA8 ? 4u : 3u) :
          (uint32_t)level_bytes(w, h, fmt));
    put32(buf + 28, mips > 1 ? mips : 0);
    put32(buf + 76, 32);
    put32(buf + 80, fmt == FOJ_STAGE332_BGRA8 ? 0x41u :
          fmt == FOJ_STAGE332_BGR8 ? 0x40u : 4u);
    put32(buf + 84, fmt == FOJ_STAGE332_BC1 ? 0x31545844u :
          fmt == FOJ_STAGE332_BC2 ? 0x33545844u : 0u);
    if (raw) {
        put32(buf + 88, fmt == FOJ_STAGE332_BGRA8 ? 32 : 24);
        put32(buf + 92, 0x00ff0000u); put32(buf + 96, 0x0000ff00u);
        put32(buf + 100, 0x000000ffu);
        put32(buf + 104, fmt == FOJ_STAGE332_BGRA8 ? 0xff000000u : 0u);
    }
    put32(buf + 108, mips > 1 ? 0x401008u : 0x1000u);
    return total;
}
static void no_change(const uint8_t *buf, size_t len) {
    uint8_t out[256]; memset(out, 0xa5, sizeof(out));
    FojStage332DdsInfo info = {77,88,99, FOJ_STAGE332_BC2,12345};
    assert(!foj_stage332_dds_decode(buf, len, out, sizeof(out), &info));
    for (size_t i = 0; i < sizeof(out); ++i) assert(out[i] == 0xa5);
    assert(info.width == 77 && info.height == 88 && info.mip_levels == 99);
    assert(info.rgba_bytes == 12345 && info.format == FOJ_STAGE332_BC2);
}
static void test_uncompressed(void) {
    uint8_t buf[512], out[256]; FojStage332DdsInfo info;
    size_t n = build(buf, sizeof(buf), FOJ_STAGE332_BGRA8, 3, 2, 2);
    uint8_t *p = buf + 128;
    for (unsigned i = 0; i < 6u; ++i) {
        p[4*i] = 20; p[4*i+1] = 60; p[4*i+2] = 90; p[4*i+3] = 140;
    }
    assert(foj_stage332_dds_decode(buf, n, out, sizeof(out), &info));
    assert(info.width == 3 && info.height == 2 && info.mip_levels == 2);
    assert(info.format == FOJ_STAGE332_BGRA8 && info.rgba_bytes == 24);
    for (unsigned i = 0; i < 6u; ++i) assert(out[4*i] == 90 &&
        out[4*i+1] == 60 && out[4*i+2] == 20 && out[4*i+3] == 140);
    no_change(buf, n-1); /* truncated tail of mip chain */
    buf[n] = 0xff; no_change(buf, n+1); /* hidden suffix */
    n = build(buf, sizeof(buf), FOJ_STAGE332_BGR8, 2, 1, 1);
    p = buf + 128;
    p[0]=9; p[1]=25; p[2]=71; p[3]=14; p[4]=44; p[5]=111;
    assert(foj_stage332_dds_decode(buf,n,out,sizeof(out),&info));
    assert(out[0] == 71 && out[1] == 25 && out[2] == 9 && out[3] == 255);
    assert(out[4] == 111 && out[5] == 44 && out[6] == 14 && out[7] == 255);
    assert(info.format == FOJ_STAGE332_BGR8);
    put32(buf+104, 0xff000000u); no_change(buf,n);
}
static void test_bc1_partial(void) {
    uint8_t buf[512], out[5*3*4]; FojStage332DdsInfo info;
    size_t n = build(buf,sizeof(buf),FOJ_STAGE332_BC1,5,3,1);
    /* Two BC1 blocks. Color endpoints are red and blue; idx=0 is red. */
    uint8_t *p=buf+128; p[0]=0x00; p[1]=0xf8; p[2]=0x1f; p[3]=0x00;
    p[8]=0x00; p[9]=0xf8; p[10]=0x1f; p[11]=0x00;
    assert(foj_stage332_dds_decode(buf,n,out,sizeof(out),&info));
    for (size_t i=0; i<15; ++i) {
        assert(out[4*i]==255 && out[4*i+1]==0 && out[4*i+2]==0 && out[4*i+3]==255);
    }
    /* c0 <= c1, BC1 index 3 is transparent. */
    p[0]=0; p[1]=0; p[2]=0xff; p[3]=0xff;
    put32(p+4, 0xffffffffu);
    assert(foj_stage332_dds_decode(buf,n,out,sizeof(out),&info));
    assert(out[0]==0 && out[1]==0 && out[2]==0 && out[3]==0);
    assert(out[4*4]==255 && out[4*4+3]==255); /* second block remains red */
    no_change(buf,n-1);
}
static void test_bc2_nibbles(void) {
    uint8_t buf[512], out[4*4*4]; FojStage332DdsInfo info;
    size_t n = build(buf,sizeof(buf),FOJ_STAGE332_BC2,4,4,1);
    uint8_t *p=buf+128;
    for (unsigned i=0;i<8;++i) p[i]= (uint8_t)(i*0x11u);
    /* BC2 must decode four-color palette even if c0 <= c1. */
    p[8]=0; p[9]=0; p[10]=0xff; p[11]=0xff;
    put32(p+12,0xffffffffu);
    assert(foj_stage332_dds_decode(buf,n,out,sizeof(out),&info));
    assert(info.format == FOJ_STAGE332_BC2);
    assert(out[0]==170 && out[1]==170 && out[2]==170 && out[3]==0);
    assert(out[4]==170 && out[5]==170 && out[6]==170 && out[7]==0);
    assert(out[4*2+3]==17 && out[4*3+3]==17);
    assert(out[4*14+3]==119 && out[4*15+3]==119);
    uint8_t same[512]; memcpy(same,buf,n);
    no_change(buf,n-1);
    put32(buf+20, 8); no_change(buf,n);
    memcpy(buf,same,n);
    put32(buf+84,0x35545844u); no_change(buf,n); /* DXT5 needs legacy route */
}
static void test_source_zero_pitch_variants(void) {
    uint8_t buf[512], out[256]; FojStage332DdsInfo info;
    for (FojStage332Format fmt = FOJ_STAGE332_BGRA8;
         fmt <= FOJ_STAGE332_BC2; fmt = (FojStage332Format)(fmt+1)) {
        /* Synthetic byte fixtures reproduce observed classic header SHAPES;
         * no original PS3 data appears in this test. */
        const unsigned width = fmt >= FOJ_STAGE332_BC1 ? 5u : 3u;
        const unsigned height = fmt >= FOJ_STAGE332_BC1 ? 3u : 2u;
        const size_t n = build(buf,sizeof(buf),fmt,width,height,2);
        put32(buf+8,0x21007u);
        put32(buf+20,0u);
        put32(buf+108,0x401008u | (fmt == FOJ_STAGE332_BGRA8 ? 2u : 0u));
        assert(foj_stage332_dds_decode(buf,n,out,sizeof(out),&info));
        assert(info.width == width && info.height == height &&
               info.mip_levels == 2 && info.format == fmt);
        /* A hybrid header must never silently pass as either profile. */
        put32(buf+20,8u); no_change(buf,n);
        put32(buf+20,0u);
        put32(buf+8,0x81007u); no_change(buf,n);
        put32(buf+8,0x21007u);
        put32(buf+108,0x401008u | (fmt == FOJ_STAGE332_BGRA8 ? 0u : 2u));
        no_change(buf,n);
    }
}
static void test_malformed_and_large(void) {
    uint8_t buf[512], out[256]; FojStage332DdsInfo info = {0};
    size_t n=build(buf,sizeof(buf),FOJ_STAGE332_BGRA8,3,2,1);
    assert(foj_stage332_dds_inspect(buf,n,&info));
    assert(!foj_stage332_dds_decode(buf,n,out,23,&info));
    assert(!foj_stage332_dds_decode(buf,n,buf,sizeof(buf),&info));
    put32(buf+16,4096); no_change(buf,n); /* 2048px bound */
    put32(buf+16,3);
    put32(buf+88,16); no_change(buf,n);
    put32(buf+88,32);
    put32(buf+8,0); no_change(buf,n);
    put32(buf+8,0x100f);
    put32(buf+108,0x401008); no_change(buf,n); /* wrong mip caps */
    put32(buf+108,0x1000);
    put32(buf+28,13); no_change(buf,n);
    put32(buf+28,0);
    put32(buf+124,1); no_change(buf,n); /* unsupported DDS layout */
    put32(buf+124,0);
    assert(foj_stage332_dds_inspect(buf,n,&info));
    assert(info.width == 3 && info.mip_levels == 1);
}
int main(void) {
    test_uncompressed(); test_bc1_partial(); test_bc2_nibbles();
    test_malformed_and_large(); test_source_zero_pitch_variants();
    puts("STAGE332_SYNTHETIC_DDS_BGRA_BGR_BC1_BC2_FAIL_CLOSED_PASS");
    return 0;
}
