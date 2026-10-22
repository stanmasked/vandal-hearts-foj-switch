/* Stage313 genuine C metamorphic proof:
 * rotating both source RGBA pages must rotate a right-edge gutter into
 * an exactly identical bottom-edge gutter, for every 256x256 pixel.
 * Host synthetic data only, never original PS3/owner assets.
 */
#include "stage313_oriented_gutter.h"
#include "stage310_page_edge_gutter.h"
#include "stage311_horizontal_gutter.h"
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

enum { EDGE=256, PIXELS=256*256 };
static void transpose(const uint8_t *a,uint8_t *b) {
    for (unsigned y=0;y<EDGE;++y)
        for (unsigned x=0;x<EDGE;++x)
            memcpy(b+((size_t)x*EDGE+y)*4u,
                   a+((size_t)y*EDGE+x)*4u,4u);
}
static void build_sources(uint8_t *a,uint8_t *b) {
    for(unsigned y=0;y<EDGE;++y) {
        for(unsigned x=0;x<EDGE;++x) {
            const size_t i=((size_t)y*EDGE+x)*4u;
            a[i]=(uint8_t)(x+3u*y);
            a[i+1]=(uint8_t)(x*2u+y);
            a[i+2]=(uint8_t)(x+2u*y);
            a[i+3]=255u;
            b[i]=(uint8_t)(255u-x-3u*y);
            b[i+1]=(uint8_t)(x+y*3u);
            b[i+2]=(uint8_t)(155u+x*3u-y);
            b[i+3]=255u;
        }
    }
}
static void verify(void) {
    const size_t count=FOJ_BC1_PAGE_RGBA_BYTES;
    uint8_t *a=(uint8_t*)malloc(count),*b=(uint8_t*)malloc(count);
    uint8_t *ta=(uint8_t*)malloc(count),*tb=(uint8_t*)malloc(count);
    uint8_t *east=(uint8_t*)malloc(count),*south=(uint8_t*)malloc(count);
    uint8_t *expected_south=(uint8_t*)malloc(count);
    uint8_t *direct=(uint8_t*)malloc(count);
    uint8_t *saved_a=(uint8_t*)malloc(count),*saved_b=(uint8_t*)malloc(count);
    assert(a&&b&&ta&&tb&&east&&south&&expected_south&&direct&&saved_a&&saved_b);
    build_sources(a,b);
    memcpy(saved_a,a,count);memcpy(saved_b,b,count);
    transpose(a,ta);transpose(b,tb);
    FojStage313GutterReport east_report={0},south_report={0};
    assert(foj_stage313_build_oriented_gutter(
        FOJ_STAGE313_EDGE_EAST,a,count,b,count,east,count,&east_report)==1);
    assert(east_report.orientation==FOJ_STAGE313_EDGE_EAST);
    assert(east_report.samples_processed==256u);
    assert(east_report.contrasting_samples>240u);
    assert(east_report.genuinely_mixed_samples>200u);
    FojStage310GutterReport ve={0};
    assert(foj_stage310_build_page_edge_gutter(
        a,count,b,count,direct,count,&ve)==1);
    assert(memcmp(east,direct,count)==0);
    assert(ve.rows==east_report.samples_processed);
    assert(ve.contrasting_edge_rows==east_report.contrasting_samples);
    assert(ve.strictly_mixed_rows==east_report.genuinely_mixed_samples);

    assert(foj_stage313_build_oriented_gutter(
        FOJ_STAGE313_EDGE_SOUTH,ta,count,tb,count,south,count,
        &south_report)==1);
    assert(south_report.orientation==FOJ_STAGE313_EDGE_SOUTH);
    assert(south_report.samples_processed==east_report.samples_processed);
    assert(south_report.contrasting_samples==east_report.contrasting_samples);
    assert(south_report.genuinely_mixed_samples==east_report.genuinely_mixed_samples);
    FojStage311HorizontalReport he={0};
    assert(foj_stage311_build_horizontal_gutter(
        ta,count,tb,count,direct,count,&he)==1);
    assert(memcmp(south,direct,count)==0);
    assert(he.columns_processed==south_report.samples_processed);
    assert(he.contrasting_columns==south_report.contrasting_samples);
    assert(he.genuinely_mixed_columns==south_report.genuinely_mixed_samples);

    transpose(east,expected_south);
    assert(memcmp(expected_south,south,count)==0);
    for(unsigned y=0;y<EDGE;++y) {
        for(unsigned x=0;x<EDGE;++x) {
            const size_t i=((size_t)y*EDGE+x)*4u;
            const size_t expected_a=((size_t)y*EDGE+255u)*4u;
            const size_t expected_b=((size_t)y*EDGE)*4u;
            assert(memcmp(east+i,x<128u?a+expected_a:b+expected_b,4u)==0);
        }
    }
    assert(memcmp(a,saved_a,count)==0);
    assert(memcmp(b,saved_b,count)==0);

    /* Reject every bad call without mutating output or report.
     * Corrupted page size, rotated/wrong enum and overlapping report
     * cannot be silently accepted by the orientation-neutral facade. */
    FojStage313GutterReport guard={FOJ_STAGE313_EDGE_SOUTH,43u,47u,53u};
    FojStage313GutterReport copy=guard;
    memset(direct,0x5a,count);
    const struct {
        FojStage313Edge side;
        const uint8_t *a,*b;
        size_t as,bs;
        uint8_t *out;
        size_t os;
        FojStage313GutterReport *report;
    } invalid[]={
        {(FojStage313Edge)0,a,b,count,count,direct,count,&guard},
        {(FojStage313Edge)3,a,b,count,count,direct,count,&guard},
        {FOJ_STAGE313_EDGE_EAST,NULL,b,count,count,direct,count,&guard},
        {FOJ_STAGE313_EDGE_SOUTH,a,NULL,count,count,direct,count,&guard},
        {FOJ_STAGE313_EDGE_EAST,a,b,count-1u,count,direct,count,&guard},
        {FOJ_STAGE313_EDGE_SOUTH,a,b,count,count+1u,direct,count,&guard},
        {FOJ_STAGE313_EDGE_EAST,a,b,count,count,direct,count-1u,&guard},
        {FOJ_STAGE313_EDGE_SOUTH,a,b,count,count,NULL,count,&guard},
        {FOJ_STAGE313_EDGE_SOUTH,a,b,count,count,direct,count,NULL},
        {FOJ_STAGE313_EDGE_EAST,a,b,count,count,a,count,&guard},
        {FOJ_STAGE313_EDGE_SOUTH,a,b,count,count,b,count,&guard},
        {FOJ_STAGE313_EDGE_EAST,a,b,count,count,direct,count,
            (FojStage313GutterReport*)(void*)a},
        {FOJ_STAGE313_EDGE_SOUTH,a,b,count,count,direct,count,
            (FojStage313GutterReport*)(void*)b},
        {FOJ_STAGE313_EDGE_EAST,a,b,count,count,direct,count,
            (FojStage313GutterReport*)(void*)(direct+4u)},
    };
    for(size_t i=0;i<sizeof(invalid)/sizeof(invalid[0]);++i) {
        assert(foj_stage313_build_oriented_gutter(
            invalid[i].side,invalid[i].a,invalid[i].as,
            invalid[i].b,invalid[i].bs,invalid[i].out,
            invalid[i].os,invalid[i].report)==0);
        assert(memcmp(&guard,&copy,sizeof(guard))==0);
        assert(memcmp(a,saved_a,count)==0);
        assert(memcmp(b,saved_b,count)==0);
        for (size_t j=0;j<count;++j)assert(direct[j]==0x5a);
    }

    /* Two flat identical pages must not be claimed as an edge blend. */
    memset(a,0x77,count);memset(b,0x77,count);
    for(unsigned s=1u;s<=2u;++s) {
        assert(foj_stage313_build_oriented_gutter(
            (FojStage313Edge)s,a,count,b,count,direct,count,&guard)==1);
        assert(guard.orientation==(FojStage313Edge)s);
        assert(guard.samples_processed==256u);
        assert(guard.contrasting_samples==0u);
        assert(guard.genuinely_mixed_samples==0u);
        for(size_t i=0;i<count;++i)assert(direct[i]==0x77);
    }
    free(a);free(b);free(ta);free(tb);free(east);free(south);
    free(expected_south);free(direct);free(saved_a);free(saved_b);
    puts("STAGE313_NATIVE_ORIENTATION_TRANSPOSE_METAMORPHIC_65536_PIXELS_PASS");
}
int main(void){verify();return 0;}
