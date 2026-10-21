/* Stage308 synthetic only. Independently call REAL Stage301 native BC1 decoder,
 * Stage303 native UV resolver, Stage308 cross-page bilinear reference.
 * Nothing accesses PS3/game files, deko3d, hardware or private assets.
 */
#include "bc1_atlas_page.h"
#include "stage308_cross_page_bilinear.h"
#include <assert.h>
#include <math.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static void put32(uint8_t *out,unsigned n) {
    out[0]=(uint8_t)n;out[1]=(uint8_t)(n>>8u);
    out[2]=(uint8_t)(n>>16u);out[3]=(uint8_t)(n>>24u);
}
static uint8_t *synthetic_dds(void) {
    uint8_t *p=(uint8_t*)calloc(FOJ_BC1_SOURCE_FILE_BYTES,1u);
    assert(p);
    memcpy(p,"DDS ",4u);put32(p+4u,124u);put32(p+8u,0x81007u);
    put32(p+12u,1024u);put32(p+16u,1024u);
    put32(p+20u,1024u*1024u/2u);put32(p+28u,1u);
    put32(p+76u,32u);put32(p+80u,4u);
    put32(p+84u,0x31545844u);put32(p+108u,0x1000u);
    for (unsigned row=0;row<256u;++row) {
        for (unsigned col=0;col<256u;++col) {
            const unsigned page_x=col/64u,page_y=row/64u;
            const int lower_half=(row%64u)>=32u;
            uint16_t color=0x0000u;
            if (page_y==1u && page_x==1u)
                color=(uint16_t)(lower_half?0xf800u:0x001fu); /* red/blue */
            if (page_y==1u && page_x==2u)
                color=(uint16_t)(lower_half?0x07e0u:0xffe0u); /* green/yellow */
            const size_t at=128u+((size_t)row*256u+col)*8u;
            p[at]=(uint8_t)color;p[at+1u]=(uint8_t)(color>>8u);
            p[at+2u]=0u;p[at+3u]=0u;
            memset(p+at+4u,0,4u);
        }
    }
    return p;
}
static void expect_rgba(const uint8_t actual[4],const uint8_t expected[4]) {
    assert(memcmp(actual,expected,4u)==0);
}
static void check_blending(const uint8_t *left,const uint8_t *right,
                           unsigned y,const uint8_t rgb_left[4],
                           const uint8_t rgb_right[4],
                           const uint8_t expected_middle[4]) {
    uint8_t got[4]={99,98,97,96};
    const float center=.5f;
    assert(foj_stage308_cross_page_bilinear(left,FOJ_BC1_PAGE_RGBA_BYTES,
        right,FOJ_BC1_PAGE_RGBA_BYTES,y,center,got));
    expect_rgba(got,expected_middle);
    assert(foj_stage308_requires_two_pages(rgb_left,rgb_right,got)==1);
    assert(foj_stage308_requires_two_pages(rgb_left,rgb_left,got)==0);
    assert(foj_stage308_requires_two_pages(rgb_left,rgb_right,rgb_left)==0);
    assert(foj_stage308_requires_two_pages(rgb_left,rgb_right,rgb_right)==0);

    const float first=511.5f/1024.f,last=512.5f/1024.f;
    assert(foj_stage308_cross_page_bilinear(left,FOJ_BC1_PAGE_RGBA_BYTES,
        right,FOJ_BC1_PAGE_RGBA_BYTES,y,first,got));
    expect_rgba(got,rgb_left);
    assert(foj_stage308_cross_page_bilinear(left,FOJ_BC1_PAGE_RGBA_BYTES,
        right,FOJ_BC1_PAGE_RGBA_BYTES,y,last,got));
    expect_rgba(got,rgb_right);
    const float quarter=(511.75f/1024.f);
    const float three_quarters=(512.25f/1024.f);
    assert(foj_stage308_cross_page_bilinear(left,FOJ_BC1_PAGE_RGBA_BYTES,
        right,FOJ_BC1_PAGE_RGBA_BYTES,y,quarter,got));
    for (unsigned k=0;k<4u;++k)
        assert(abs((int)got[k]-(int)lroundf(.75f*rgb_left[k]+.25f*rgb_right[k]))<=1);
    assert(foj_stage308_cross_page_bilinear(left,FOJ_BC1_PAGE_RGBA_BYTES,
        right,FOJ_BC1_PAGE_RGBA_BYTES,y,three_quarters,got));
    for (unsigned k=0;k<4u;++k)
        assert(abs((int)got[k]-(int)lroundf(.25f*rgb_left[k]+.75f*rgb_right[k]))<=1);
}
int main(void) {
    uint8_t *src=synthetic_dds();
    uint8_t *left=(uint8_t*)malloc(FOJ_BC1_PAGE_RGBA_BYTES);
    uint8_t *right=(uint8_t*)malloc(FOJ_BC1_PAGE_RGBA_BYTES);
    assert(left && right);
    FojAtlasRgba8Info li={0},ri={0};
    assert(foj_bc1_1024_decode_page(
        src,FOJ_BC1_SOURCE_FILE_BYTES,1,1,left,
        FOJ_BC1_PAGE_RGBA_BYTES,&li)==1);
    assert(foj_bc1_1024_decode_page(
        src,FOJ_BC1_SOURCE_FILE_BYTES,2,1,right,
        FOJ_BC1_PAGE_RGBA_BYTES,&ri)==1);
    assert(li.width==256u && li.height==256u);
    assert(ri.width==256u && ri.height==256u);
    const uint8_t blue[4]={0,0,255,255};
    const uint8_t yellow[4]={255,255,0,255};
    const uint8_t midpoint1[4]={128,128,128,255};
    const uint8_t red[4]={255,0,0,255};
    const uint8_t green[4]={0,255,0,255};
    const uint8_t midpoint2[4]={128,128,0,255};
    for (unsigned y=0;y<256u;y+=127u) {
        const unsigned at=y*256u*4u;
        if (y<128u) {
            expect_rgba(left+at+255u*4u,blue);
            expect_rgba(right+at,yellow);
            check_blending(left,right,y,blue,yellow,midpoint1);
        } else {
            expect_rgba(left+at+255u*4u,red);
            expect_rgba(right+at,green);
            check_blending(left,right,y,red,green,midpoint2);
        }
    }
    const uint8_t guard[4]={0xa5,0x5a,0xc3,0x3c};
    uint8_t out[4];
    struct {
        const uint8_t *l,*r;
        unsigned y;
        float u;
    } fail[]={
        {NULL,right,0,.5f},{left,NULL,0,.5f},
        {left,right,256,.5f},{left,right,4294967295u,.5f},
        {left,right,0,NAN},{left,right,0,INFINITY},
        {left,right,0,-INFINITY},{left,right,0,-1.f},
        {left,right,0,0.f},{left,right,0,1.f},
        {left,right,0,nextafterf(511.5f/1024.f,0.f)},
        {left,right,0,nextafterf(512.5f/1024.f,1.f)},
    };
    for (unsigned i=0;i<sizeof(fail)/sizeof(fail[0]);++i) {
        memcpy(out,guard,4u);
        assert(foj_stage308_cross_page_bilinear(
            fail[i].l,FOJ_BC1_PAGE_RGBA_BYTES,
            fail[i].r,FOJ_BC1_PAGE_RGBA_BYTES,fail[i].y,fail[i].u,out)==0);
        expect_rgba(out,guard);
    }
    assert(foj_stage308_cross_page_bilinear(
        left,FOJ_BC1_PAGE_RGBA_BYTES,right,FOJ_BC1_PAGE_RGBA_BYTES,
        0,.5f,NULL)==0);
    for (unsigned side=0;side<2u;++side) {
        for (unsigned kind=0;kind<3u;++kind) {
            const size_t wrong=kind==0?0u:
                kind==1?FOJ_BC1_PAGE_RGBA_BYTES-1u:
                        FOJ_BC1_PAGE_RGBA_BYTES+1u;
            memcpy(out,guard,4u);
            assert(foj_stage308_cross_page_bilinear(
                left,side==0u?wrong:FOJ_BC1_PAGE_RGBA_BYTES,
                right,side==1u?wrong:FOJ_BC1_PAGE_RGBA_BYTES,
                0,.5f,out)==0);
            expect_rgba(out,guard);
        }
    }
    assert(foj_stage308_requires_two_pages(NULL,blue,midpoint1)==0);
    assert(foj_stage308_requires_two_pages(blue,NULL,midpoint1)==0);
    assert(foj_stage308_requires_two_pages(blue,yellow,NULL)==0);
    const uint8_t outside[4]={255,0,255,255};
    assert(foj_stage308_requires_two_pages(blue,yellow,outside)==0);
    free(src);free(left);free(right);
    puts("STAGE308_REAL_C_CROSS_PAGE_BILINEAR_REFERENCE_AND_CLAMP_NEGATIVE_PASS");
    return 0;
}
