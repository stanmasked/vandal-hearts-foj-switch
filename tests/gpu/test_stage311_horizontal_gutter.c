/* Stage311 native generated-only BC1 pages (1,1) and (1,2):
 * eight changing column-color pairs, true horizontal seam between atlas
 * texel rows 511 and 512. Never reads PS3 / owner-held resources.
 */
#include "stage311_horizontal_gutter.h"
#include <assert.h>
#include <math.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static const uint16_t colors[2][8]={
    {0x001fu,0xf800u,0x07e0u,0xffe0u,0xf81fu,0x07ffu,0xffffu,0x0000u},
    {0xffe0u,0x07e0u,0x001fu,0xf800u,0x07ffu,0xf81fu,0x0000u,0xffffu}
};
static void put32(uint8_t *p,unsigned v) {
    p[0]=(uint8_t)v;p[1]=(uint8_t)(v>>8u);
    p[2]=(uint8_t)(v>>16u);p[3]=(uint8_t)(v>>24u);
}
static void expand(uint16_t v,uint8_t p[4]) {
    const unsigned r=(v>>11u)&31u,g=(v>>5u)&63u,b=v&31u;
    p[0]=(uint8_t)((r<<3u)|(r>>2u));
    p[1]=(uint8_t)((g<<2u)|(g>>4u));
    p[2]=(uint8_t)((b<<3u)|(b>>2u));
    p[3]=255u;
}
static uint8_t *source_dds(void) {
    uint8_t *p=(uint8_t*)calloc(FOJ_BC1_SOURCE_FILE_BYTES,1u);
    assert(p);
    memcpy(p,"DDS ",4u);put32(p+4u,124u);
    put32(p+8u,0x81007u);put32(p+12u,1024u);
    put32(p+16u,1024u);put32(p+20u,1024u*1024u/2u);
    put32(p+28u,1u);put32(p+76u,32u);put32(p+80u,4u);
    put32(p+84u,0x31545844u);put32(p+108u,0x1000u);
    for (unsigned by=0;by<256u;++by) {
        for(unsigned bx=0;bx<256u;++bx) {
            const unsigned px=bx/64u,py=by/64u;
            const uint16_t col=(px==1u && (py==1u || py==2u))?
                colors[py-1u][(bx%64u)/8u]:0u;
            const size_t at=128u+((size_t)by*256u+bx)*8u;
            p[at]=(uint8_t)col;p[at+1]=(uint8_t)(col>>8u);
        }
    }
    return p;
}
int main(void) {
    uint8_t *dds=source_dds();
    uint8_t *top=(uint8_t*)malloc(FOJ_BC1_PAGE_RGBA_BYTES);
    uint8_t *bottom=(uint8_t*)malloc(FOJ_BC1_PAGE_RGBA_BYTES);
    uint8_t *gutter=(uint8_t*)malloc(FOJ_BC1_PAGE_RGBA_BYTES);
    uint8_t *copytop=(uint8_t*)malloc(FOJ_BC1_PAGE_RGBA_BYTES);
    uint8_t *copybottom=(uint8_t*)malloc(FOJ_BC1_PAGE_RGBA_BYTES);
    assert(top && bottom && gutter && copytop && copybottom);
    FojAtlasRgba8Info t={0},b={0};
    assert(foj_bc1_1024_decode_page(dds,FOJ_BC1_SOURCE_FILE_BYTES,
        1u,1u,top,FOJ_BC1_PAGE_RGBA_BYTES,&t)==1);
    assert(foj_bc1_1024_decode_page(dds,FOJ_BC1_SOURCE_FILE_BYTES,
        1u,2u,bottom,FOJ_BC1_PAGE_RGBA_BYTES,&b)==1);
    assert(t.width==256u && t.height==256u);
    assert(b.width==256u && b.height==256u);
    memcpy(copytop,top,FOJ_BC1_PAGE_RGBA_BYTES);
    memcpy(copybottom,bottom,FOJ_BC1_PAGE_RGBA_BYTES);
    memset(gutter,0x43,FOJ_BC1_PAGE_RGBA_BYTES);
    FojStage311HorizontalReport info={0};
    assert(foj_stage311_build_horizontal_gutter(
        top,FOJ_BC1_PAGE_RGBA_BYTES,bottom,FOJ_BC1_PAGE_RGBA_BYTES,
        gutter,FOJ_BC1_PAGE_RGBA_BYTES,&info)==1);
    assert(info.columns_processed==256u);
    assert(info.contrasting_columns==256u);
    assert(info.genuinely_mixed_columns==256u);
    for(unsigned x=0;x<256u;++x) {
        uint8_t up[4],down[4],mixed[4]={0};
        expand(colors[0][x/32u],up);
        expand(colors[1][x/32u],down);
        assert(memcmp(top+((size_t)255u*256u+x)*4u,up,4u)==0);
        assert(memcmp(bottom+(size_t)x*4u,down,4u)==0);
        assert(foj_stage311_horizontal_bilinear(
            top,FOJ_BC1_PAGE_RGBA_BYTES,bottom,
            FOJ_BC1_PAGE_RGBA_BYTES,x,.5f,mixed)==1);
        for (unsigned k=0;k<4u;++k)
            assert(mixed[k]==(uint8_t)((up[k]+down[k]+1u)/2u));
        for(unsigned y=0;y<256u;++y) {
            const uint8_t *expected=y<128u?up:down;
            assert(memcmp(gutter+((size_t)y*256u+x)*4u,expected,4u)==0);
        }
        const float near_top=511.5f/1024.f;
        const float near_bottom=512.5f/1024.f;
        assert(foj_stage311_horizontal_bilinear(
            top,FOJ_BC1_PAGE_RGBA_BYTES,bottom,
            FOJ_BC1_PAGE_RGBA_BYTES,x,near_top,mixed)==1);
        assert(memcmp(mixed,up,4u)==0);
        assert(foj_stage311_horizontal_bilinear(
            top,FOJ_BC1_PAGE_RGBA_BYTES,bottom,
            FOJ_BC1_PAGE_RGBA_BYTES,x,near_bottom,mixed)==1);
        assert(memcmp(mixed,down,4u)==0);
    }
    assert(memcmp(top,copytop,FOJ_BC1_PAGE_RGBA_BYTES)==0);
    assert(memcmp(bottom,copybottom,FOJ_BC1_PAGE_RGBA_BYTES)==0);
    uint8_t output_guard[4]={0x12,0x43,0x65,0x87},out[4];
    for (unsigned n=0;n<11u;++n) {
        memcpy(out,output_guard,4u);
        const float v=(n==0u)?NAN:(n==1u)?INFINITY:
            (n==2u)?-INFINITY:(n==3u)?-1.f:(n==4u)?1.f:
            (n==5u)?nextafterf(511.5f/1024.f,0.f):
            (n==6u)?nextafterf(512.5f/1024.f,1.f):.5f;
        assert(foj_stage311_horizontal_bilinear(
            n==7u?NULL:top,
            n==8u?0u:FOJ_BC1_PAGE_RGBA_BYTES,
            n==9u?NULL:bottom,
            FOJ_BC1_PAGE_RGBA_BYTES,n==10u?256u:0u,v,out)==0);
        assert(memcmp(out,output_guard,4u)==0);
    }
    struct {
        const uint8_t *a,*b;
        size_t as,bs;
        uint8_t *out;
        size_t os;
        FojStage311HorizontalReport *report;
    } bad[]={
        {NULL,bottom,FOJ_BC1_PAGE_RGBA_BYTES,FOJ_BC1_PAGE_RGBA_BYTES,
         gutter,FOJ_BC1_PAGE_RGBA_BYTES,&info},
        {top,NULL,FOJ_BC1_PAGE_RGBA_BYTES,FOJ_BC1_PAGE_RGBA_BYTES,
         gutter,FOJ_BC1_PAGE_RGBA_BYTES,&info},
        {top,bottom,FOJ_BC1_PAGE_RGBA_BYTES-1u,FOJ_BC1_PAGE_RGBA_BYTES,
         gutter,FOJ_BC1_PAGE_RGBA_BYTES,&info},
        {top,bottom,FOJ_BC1_PAGE_RGBA_BYTES,FOJ_BC1_PAGE_RGBA_BYTES+1u,
         gutter,FOJ_BC1_PAGE_RGBA_BYTES,&info},
        {top,bottom,FOJ_BC1_PAGE_RGBA_BYTES,FOJ_BC1_PAGE_RGBA_BYTES,
         gutter,FOJ_BC1_PAGE_RGBA_BYTES-1u,&info},
        {top,bottom,FOJ_BC1_PAGE_RGBA_BYTES,FOJ_BC1_PAGE_RGBA_BYTES,
         top,FOJ_BC1_PAGE_RGBA_BYTES,&info},
        {top,bottom,FOJ_BC1_PAGE_RGBA_BYTES,FOJ_BC1_PAGE_RGBA_BYTES,
         bottom,FOJ_BC1_PAGE_RGBA_BYTES,&info},
        {top,bottom,FOJ_BC1_PAGE_RGBA_BYTES,FOJ_BC1_PAGE_RGBA_BYTES,
         gutter,FOJ_BC1_PAGE_RGBA_BYTES,NULL},
        {top,bottom,FOJ_BC1_PAGE_RGBA_BYTES,FOJ_BC1_PAGE_RGBA_BYTES,
         gutter,FOJ_BC1_PAGE_RGBA_BYTES,
         (FojStage311HorizontalReport*)(void*)top},
        {top,bottom,FOJ_BC1_PAGE_RGBA_BYTES,FOJ_BC1_PAGE_RGBA_BYTES,
         gutter,FOJ_BC1_PAGE_RGBA_BYTES,
         (FojStage311HorizontalReport*)(void*)bottom},
        {top,bottom,FOJ_BC1_PAGE_RGBA_BYTES,FOJ_BC1_PAGE_RGBA_BYTES,
         gutter,FOJ_BC1_PAGE_RGBA_BYTES,
         (FojStage311HorizontalReport*)(void*)gutter},
    };
    for(size_t i=0;i<sizeof(bad)/sizeof(bad[0]);++i) {
        FojStage311HorizontalReport saved=info;
        assert(foj_stage311_build_horizontal_gutter(
            bad[i].a,bad[i].as,bad[i].b,bad[i].bs,
            bad[i].out,bad[i].os,bad[i].report)==0);
        assert(memcmp(&info,&saved,sizeof(info))==0);
        assert(memcmp(top,copytop,FOJ_BC1_PAGE_RGBA_BYTES)==0);
        assert(memcmp(bottom,copybottom,FOJ_BC1_PAGE_RGBA_BYTES)==0);
    }
    /* No forced "contrast" when both source pages happen to agree. */
    memset(gutter,0,FOJ_BC1_PAGE_RGBA_BYTES);
    assert(foj_stage311_build_horizontal_gutter(
        top,FOJ_BC1_PAGE_RGBA_BYTES,top,FOJ_BC1_PAGE_RGBA_BYTES,
        gutter,FOJ_BC1_PAGE_RGBA_BYTES,&info)==1);
    assert(info.columns_processed==256u);
    assert(info.contrasting_columns==0u);
    assert(info.genuinely_mixed_columns==0u);
    free(dds);free(top);free(bottom);free(gutter);
    free(copytop);free(copybottom);
    puts("STAGE311_NATIVE_HORIZONTAL_BC1_256_COLUMNS_EIGHT_COLOR_PAIRS_AND_FAIL_CLOSED_PASS");
    return 0;
}
