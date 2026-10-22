/* Stage310: actual native BC1 decoder produces 8 distinct per-row pairs.
 * Generalized gutter builder must preserve every decoded source edge.
 * Inputs are invented DDS bytes, not original NPEB00148 data.
 */
#include "stage310_page_edge_gutter.h"
#include "stage308_cross_page_bilinear.h"
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static const uint16_t colors[2][8]={
    {0x001fu,0xf800u,0x07e0u,0xffe0u,0xf81fu,0x07ffu,0xffffu,0x0000u},
    {0xffe0u,0x07e0u,0x001fu,0xf800u,0x07ffu,0xf81fu,0x0000u,0xffffu}
};
static void put32(uint8_t *p,uint32_t n) {
    p[0]=(uint8_t)n;p[1]=(uint8_t)(n>>8u);
    p[2]=(uint8_t)(n>>16u);p[3]=(uint8_t)(n>>24u);
}
static void decode565(uint16_t v,uint8_t out[4]) {
    const unsigned r=(v>>11u)&31u,g=(v>>5u)&63u,b=v&31u;
    out[0]=(uint8_t)((r<<3u)|(r>>2u));
    out[1]=(uint8_t)((g<<2u)|(g>>4u));
    out[2]=(uint8_t)((b<<3u)|(b>>2u));
    out[3]=255u;
}
static uint8_t *dds(void) {
    uint8_t *p=(uint8_t*)calloc(FOJ_BC1_SOURCE_FILE_BYTES,1);
    assert(p);
    memcpy(p,"DDS ",4u);put32(p+4u,124u);put32(p+8u,0x81007u);
    put32(p+12u,1024u);put32(p+16u,1024u);
    put32(p+20u,1024u*1024u/2u);put32(p+28u,1u);
    put32(p+76u,32u);put32(p+80u,4u);
    put32(p+84u,0x31545844u);put32(p+108u,0x1000u);
    for(unsigned y=0;y<256u;++y) {
        for(unsigned x=0;x<256u;++x) {
            const unsigned page_x=x/64u,page_y=y/64u;
            uint16_t endpoint=0x0000u;
            if(page_y==1u && (page_x==1u || page_x==2u))
                endpoint=colors[page_x-1u][(y%64u)/8u];
            const size_t at=128u+((size_t)y*256u+x)*8u;
            p[at]=(uint8_t)endpoint;
            p[at+1]=(uint8_t)(endpoint>>8u);
            /* Index 0 in all 16 BC1 texels, so every expanded block is
             * exactly the intended RGB565 color, alpha=255. */
        }
    }
    return p;
}
static void run(void) {
    uint8_t *source=dds();
    uint8_t *left=(uint8_t*)malloc(FOJ_BC1_PAGE_RGBA_BYTES);
    uint8_t *right=(uint8_t*)malloc(FOJ_BC1_PAGE_RGBA_BYTES);
    uint8_t *out=(uint8_t*)malloc(FOJ_BC1_PAGE_RGBA_BYTES);
    uint8_t *copy_left=(uint8_t*)malloc(FOJ_BC1_PAGE_RGBA_BYTES);
    uint8_t *copy_right=(uint8_t*)malloc(FOJ_BC1_PAGE_RGBA_BYTES);
    assert(left && right && out && copy_left && copy_right);
    FojAtlasRgba8Info left_meta={0},right_meta={0};
    assert(foj_bc1_1024_decode_page(source,FOJ_BC1_SOURCE_FILE_BYTES,
        1u,1u,left,FOJ_BC1_PAGE_RGBA_BYTES,&left_meta)==1);
    assert(foj_bc1_1024_decode_page(source,FOJ_BC1_SOURCE_FILE_BYTES,
        2u,1u,right,FOJ_BC1_PAGE_RGBA_BYTES,&right_meta)==1);
    assert(left_meta.width==256u && left_meta.height==256u);
    assert(right_meta.width==256u && right_meta.height==256u);
    memcpy(copy_left,left,FOJ_BC1_PAGE_RGBA_BYTES);
    memcpy(copy_right,right,FOJ_BC1_PAGE_RGBA_BYTES);
    memset(out,0xba,FOJ_BC1_PAGE_RGBA_BYTES);
    FojStage310GutterReport report={0};
    assert(foj_stage310_build_page_edge_gutter(
        left,FOJ_BC1_PAGE_RGBA_BYTES,right,FOJ_BC1_PAGE_RGBA_BYTES,
        out,FOJ_BC1_PAGE_RGBA_BYTES,&report)==1);
    assert(report.rows==256u);
    assert(report.contrasting_edge_rows==256u);
    assert(report.strictly_mixed_rows==256u);
    for(unsigned y=0;y<256u;++y) {
        const unsigned band=y/32u;
        uint8_t expected_left[4],expected_right[4];
        decode565(colors[0][band],expected_left);
        decode565(colors[1][band],expected_right);
        assert(memcmp(left+((size_t)y*256u+255u)*4u,
                      expected_left,4u)==0);
        assert(memcmp(right+(size_t)y*256u*4u,
                      expected_right,4u)==0);
        for(unsigned x=0;x<256u;++x) {
            const uint8_t *e=x<128u?expected_left:expected_right;
            assert(memcmp(out+((size_t)y*256u+x)*4u,e,4u)==0);
        }
        uint8_t mix[4]={0};
        assert(foj_stage308_cross_page_bilinear(
            left,FOJ_BC1_PAGE_RGBA_BYTES,
            right,FOJ_BC1_PAGE_RGBA_BYTES,y,.5f,mix)==1);
        assert(foj_stage308_requires_two_pages(
            expected_left,expected_right,mix)==1);
    }
    assert(memcmp(copy_left,left,FOJ_BC1_PAGE_RGBA_BYTES)==0);
    assert(memcmp(copy_right,right,FOJ_BC1_PAGE_RGBA_BYTES)==0);

    const uint8_t guard[4]={0x5a,0x25,0xc3,0xe7};
    uint8_t *testout=(uint8_t*)malloc(FOJ_BC1_PAGE_RGBA_BYTES);
    assert(testout);
    struct Case {
        const uint8_t *l,*r;
        size_t lb,rb;
        uint8_t *dst;
        size_t dest_bytes;
        int have_report;
    } rejected[]={
        {NULL,right,FOJ_BC1_PAGE_RGBA_BYTES,FOJ_BC1_PAGE_RGBA_BYTES,
         testout,FOJ_BC1_PAGE_RGBA_BYTES,1},
        {left,NULL,FOJ_BC1_PAGE_RGBA_BYTES,FOJ_BC1_PAGE_RGBA_BYTES,
         testout,FOJ_BC1_PAGE_RGBA_BYTES,1},
        {left,right,FOJ_BC1_PAGE_RGBA_BYTES-1u,FOJ_BC1_PAGE_RGBA_BYTES,
         testout,FOJ_BC1_PAGE_RGBA_BYTES,1},
        {left,right,FOJ_BC1_PAGE_RGBA_BYTES,FOJ_BC1_PAGE_RGBA_BYTES+1u,
         testout,FOJ_BC1_PAGE_RGBA_BYTES,1},
        {left,right,FOJ_BC1_PAGE_RGBA_BYTES,FOJ_BC1_PAGE_RGBA_BYTES,
         testout,FOJ_BC1_PAGE_RGBA_BYTES-1u,1},
        {left,right,FOJ_BC1_PAGE_RGBA_BYTES,FOJ_BC1_PAGE_RGBA_BYTES,
         testout,FOJ_BC1_PAGE_RGBA_BYTES,0},
        {left,right,FOJ_BC1_PAGE_RGBA_BYTES,FOJ_BC1_PAGE_RGBA_BYTES,
         left,FOJ_BC1_PAGE_RGBA_BYTES,1},
        {left,right,FOJ_BC1_PAGE_RGBA_BYTES,FOJ_BC1_PAGE_RGBA_BYTES,
         right,FOJ_BC1_PAGE_RGBA_BYTES,1},
    };
    for(size_t i=0;i<sizeof(rejected)/sizeof(rejected[0]);++i) {
        for(size_t j=0;j<FOJ_BC1_PAGE_RGBA_BYTES;j+=4u)
            memcpy(testout+j,guard,4u);
        FojStage310GutterReport unchanged={55u,66u,77u};
        const struct Case c=rejected[i];
        FojStage310GutterReport *p=c.have_report?&unchanged:NULL;
        assert(foj_stage310_build_page_edge_gutter(
            c.l,c.lb,c.r,c.rb,c.dst,c.dest_bytes,p)==0);
        assert(unchanged.rows==55u && unchanged.contrasting_edge_rows==66u &&
               unchanged.strictly_mixed_rows==77u);
        if(c.dst==testout)
            for(size_t j=0;j<FOJ_BC1_PAGE_RGBA_BYTES;j+=4u)
                assert(memcmp(testout+j,guard,4u)==0);
    }
    /* Caller report may not write into either supposedly immutable
     * decoded source page. A partially overlapping report is refused. */
    for (unsigned side=0;side<2u;++side) {
        FojStage310GutterReport *report_alias=
            (FojStage310GutterReport*)(void*)(side==0u?left:right);
        memset(testout,0x5a,FOJ_BC1_PAGE_RGBA_BYTES);
        assert(foj_stage310_build_page_edge_gutter(
            left,FOJ_BC1_PAGE_RGBA_BYTES,
            right,FOJ_BC1_PAGE_RGBA_BYTES,
            testout,FOJ_BC1_PAGE_RGBA_BYTES,report_alias)==0);
        for(size_t k=0;k<FOJ_BC1_PAGE_RGBA_BYTES;++k)
            assert(testout[k]==0x5au);
    }
    assert(memcmp(copy_left,left,FOJ_BC1_PAGE_RGBA_BYTES)==0);
    assert(memcmp(copy_right,right,FOJ_BC1_PAGE_RGBA_BYTES)==0);

    assert(memcmp(copy_left,left,FOJ_BC1_PAGE_RGBA_BYTES)==0);
    assert(memcmp(copy_right,right,FOJ_BC1_PAGE_RGBA_BYTES)==0);

    /* Contract must also support two identical edge colors: gutter
     * still draws correctly, but report cannot falsely claim a mix. */
    memset(testout,0,FOJ_BC1_PAGE_RGBA_BYTES);
    assert(foj_stage310_build_page_edge_gutter(
        left,FOJ_BC1_PAGE_RGBA_BYTES,left,FOJ_BC1_PAGE_RGBA_BYTES,
        testout,FOJ_BC1_PAGE_RGBA_BYTES,&report)==1);
    assert(report.rows==256u);
    assert(report.contrasting_edge_rows==0u);
    assert(report.strictly_mixed_rows==0u);
    free(source);free(left);free(right);free(out);
    free(copy_left);free(copy_right);free(testout);
    puts("STAGE310_NATIVE_256_ROWS_EIGHT_BC1_PAIRS_GENERIC_GUTTER_PASS");
}
int main(void){run();return 0;}
