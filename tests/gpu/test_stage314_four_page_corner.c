/* Stage314: four actually C-decoded synthetic 1024 BC1 pages meet
 * at atlas texel corners (511,511),(512,511),(511,512),(512,512).
 * Original FoJ PS3 game assets are never included.
 */
#include "stage314_four_page_corner.h"
#include <assert.h>
#include <math.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

enum { PAGE_BYTES=FOJ_BC1_PAGE_RGBA_BYTES };
static const uint16_t color565[4]={
    0xf800u,0x07e0u,0x001fu,0xffffu
};
static const uint8_t expected[4][4]={
    {255,0,0,255},{0,255,0,255},
    {0,0,255,255},{255,255,255,255}
};
static void put32(uint8_t *p,uint32_t v) {
    p[0]=(uint8_t)v;p[1]=(uint8_t)(v>>8u);
    p[2]=(uint8_t)(v>>16u);p[3]=(uint8_t)(v>>24u);
}
static uint8_t *synthetic_dds(void) {
    uint8_t *dds=(uint8_t*)calloc(FOJ_BC1_SOURCE_FILE_BYTES,1u);
    assert(dds);
    memcpy(dds,"DDS ",4u);
    put32(dds+4u,124u);put32(dds+8u,0x81007u);
    put32(dds+12u,1024u);put32(dds+16u,1024u);
    put32(dds+20u,1024u*1024u/2u);put32(dds+28u,1u);
    put32(dds+76u,32u);put32(dds+80u,4u);
    put32(dds+84u,0x31545844u);put32(dds+108u,0x1000u);
    for(unsigned by=0;by<256u;++by) {
        for(unsigned bx=0;bx<256u;++bx) {
            const unsigned page_x=bx/64u,page_y=by/64u;
            uint16_t c=0u;
            if((page_x==1u || page_x==2u) &&
               (page_y==1u || page_y==2u))
                c=color565[(page_y-1u)*2u+page_x-1u];
            const size_t at=128u+((size_t)by*256u+bx)*8u;
            dds[at]=(uint8_t)c;dds[at+1]=(uint8_t)(c>>8u);
            /* BC1 selector 0: every decoded pixel equals endpoint 0. */
        }
    }
    return dds;
}
static float coord(unsigned numerator_quarters) {
    return (511.5f+.25f*numerator_quarters)/1024.f;
}
static void expected_bilinear(unsigned quarter_x,unsigned quarter_y,
                              uint8_t out[4]) {
    const float x=(float)quarter_x/4.f,y=(float)quarter_y/4.f;
    for(unsigned k=0;k<4u;++k) {
        const float top=(1.f-x)*expected[0][k]+x*expected[1][k];
        const float bottom=(1.f-x)*expected[2][k]+x*expected[3][k];
        out[k]=(uint8_t)floorf((1.f-y)*top+y*bottom+.5f);
    }
}
static void run(void) {
    uint8_t *dds=synthetic_dds();
    uint8_t *pages[4]={0};
    uint8_t *saved[4]={0};
    for(unsigned i=0;i<4u;++i) {
        pages[i]=(uint8_t*)malloc(PAGE_BYTES);
        saved[i]=(uint8_t*)malloc(PAGE_BYTES);
        assert(pages[i] && saved[i]);
        FojAtlasRgba8Info meta={0};
        assert(foj_bc1_1024_decode_page(dds,FOJ_BC1_SOURCE_FILE_BYTES,
            1u+i%2u,1u+i/2u,pages[i],PAGE_BYTES,&meta)==1);
        assert(meta.width==256u && meta.height==256u);
        assert(meta.pixel_bytes==PAGE_BYTES);
        for(size_t at=0;at<PAGE_BYTES;at+=4u)
            assert(memcmp(pages[i]+at,expected[i],4u)==0);
        memcpy(saved[i],pages[i],PAGE_BYTES);
    }
    for (unsigned x=0;x<=4u;++x)
        for(unsigned y=0;y<=4u;++y) {
            uint8_t actual[4]={0},reference[4];
            expected_bilinear(x,y,reference);
            assert(foj_stage314_four_page_bilinear(
                pages[0],PAGE_BYTES,pages[1],PAGE_BYTES,
                pages[2],PAGE_BYTES,pages[3],PAGE_BYTES,
                coord(x),coord(y),actual)==1);
            assert(memcmp(actual,reference,4u)==0);
            if(x==2u && y==2u) {
                assert(actual[0]==128u && actual[1]==128u &&
                       actual[2]==128u && actual[3]==255u);
                assert(foj_stage314_requires_four_page_mix(
                    expected,actual)==1);
            }
        }
    /* Four corner positions must return exactly their own source
     * samples without contaminating an adjacent page. */
    for(unsigned i=0;i<4u;++i) {
        uint8_t result[4]={0};
        assert(foj_stage314_four_page_bilinear(
            pages[0],PAGE_BYTES,pages[1],PAGE_BYTES,
            pages[2],PAGE_BYTES,pages[3],PAGE_BYTES,
            coord(i%2u?4u:0u),coord(i/2u?4u:0u),result)==1);
        assert(memcmp(result,expected[i],4u)==0);
    }
    /* Alpha from four independently owned RGBA pages, with exactly one
     * final rounding step; alpha is not hardcoded to opaque. */
    const unsigned xcorner[4]={255u,0u,255u,0u};
    const unsigned ycorner[4]={255u,255u,0u,0u};
    const uint8_t alpha[4]={0u,64u,192u,255u};
    for(unsigned i=0;i<4u;++i) {
        const size_t at=((size_t)ycorner[i]*256u+xcorner[i])*4u+3u;
        pages[i][at]=alpha[i];
    }
    uint8_t mixed_alpha[4]={0};
    assert(foj_stage314_four_page_bilinear(
        pages[0],PAGE_BYTES,pages[1],PAGE_BYTES,
        pages[2],PAGE_BYTES,pages[3],PAGE_BYTES,
        .5f,.5f,mixed_alpha)==1);
    assert(mixed_alpha[3]==128u);
    assert(mixed_alpha[0]==128u && mixed_alpha[1]==128u &&
           mixed_alpha[2]==128u);
    for(unsigned i=0;i<4u;++i)
        pages[i][((size_t)ycorner[i]*256u+xcorner[i])*4u+3u]=255u;
    for(unsigned i=0;i<4u;++i)
        assert(memcmp(pages[i],saved[i],PAGE_BYTES)==0);

    /* Reject bogus UV and source bounds without touching output. */
    const float bad_coordinates[]={
        NAN,INFINITY,-INFINITY,-1.f,1.f,
        nextafterf(coord(0u),0.f),
        nextafterf(coord(4u),1.f)
    };
    uint8_t out[4]={77u,88u,99u,111u};
    const uint8_t guard[4]={77u,88u,99u,111u};
    for(size_t i=0;i<sizeof(bad_coordinates)/sizeof(bad_coordinates[0]);++i) {
        assert(foj_stage314_four_page_bilinear(
            pages[0],PAGE_BYTES,pages[1],PAGE_BYTES,
            pages[2],PAGE_BYTES,pages[3],PAGE_BYTES,
            bad_coordinates[i],.5f,out)==0);
        assert(memcmp(out,guard,4u)==0);
        assert(foj_stage314_four_page_bilinear(
            pages[0],PAGE_BYTES,pages[1],PAGE_BYTES,
            pages[2],PAGE_BYTES,pages[3],PAGE_BYTES,
            .5f,bad_coordinates[i],out)==0);
        assert(memcmp(out,guard,4u)==0);
    }
    for(unsigned i=0;i<4u;++i) {
        const size_t short_size=PAGE_BYTES-1u,extra_size=PAGE_BYTES+1u;
        size_t lengths[4]={PAGE_BYTES,PAGE_BYTES,PAGE_BYTES,PAGE_BYTES};
        lengths[i]=short_size;
        assert(foj_stage314_four_page_bilinear(
            pages[0],lengths[0],pages[1],lengths[1],
            pages[2],lengths[2],pages[3],lengths[3],
            .5f,.5f,out)==0);
        assert(memcmp(out,guard,4u)==0);
        lengths[i]=extra_size;
        assert(foj_stage314_four_page_bilinear(
            pages[0],lengths[0],pages[1],lengths[1],
            pages[2],lengths[2],pages[3],lengths[3],
            .5f,.5f,out)==0);
        assert(memcmp(out,guard,4u)==0);
        const uint8_t *ptrs[4]={pages[0],pages[1],pages[2],pages[3]};
        ptrs[i]=NULL;
        assert(foj_stage314_four_page_bilinear(
            ptrs[0],PAGE_BYTES,ptrs[1],PAGE_BYTES,
            ptrs[2],PAGE_BYTES,ptrs[3],PAGE_BYTES,
            .5f,.5f,out)==0);
        assert(memcmp(out,guard,4u)==0);
        /* Output must never alias any of the four immutable source
         * pages, including a four-byte slice inside the payload. */
        assert(foj_stage314_four_page_bilinear(
            pages[0],PAGE_BYTES,pages[1],PAGE_BYTES,
            pages[2],PAGE_BYTES,pages[3],PAGE_BYTES,
            .5f,.5f,pages[i]+128u)==0);
        assert(memcmp(pages[i],saved[i],PAGE_BYTES)==0);
    }
    assert(foj_stage314_four_page_bilinear(
        pages[0],PAGE_BYTES,pages[1],PAGE_BYTES,
        pages[2],PAGE_BYTES,pages[3],PAGE_BYTES,
        .5f,.5f,NULL)==0);
    uint8_t edge_horizontal[4]={128u,128u,0u,255u};
    uint8_t equal_to_corner[4]={255u,0u,0u,255u};
    assert(foj_stage314_requires_four_page_mix(
        expected,edge_horizontal)==0);
    assert(foj_stage314_requires_four_page_mix(
        expected,equal_to_corner)==0);
    assert(foj_stage314_requires_four_page_mix(NULL,guard)==0);
    assert(foj_stage314_requires_four_page_mix(expected,NULL)==0);
    for(unsigned i=0;i<4u;++i) {
        assert(memcmp(pages[i],saved[i],PAGE_BYTES)==0);
        free(pages[i]);free(saved[i]);
    }
    free(dds);
    puts("STAGE314_NATIVE_FOUR_PAGE_BC1_CORNER_25_UVS_ALPHA_AND_FAIL_CLOSED_PASS");
}
int main(void){run();return 0;}
