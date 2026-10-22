/* Stage315 host-native corner material: synthetic source bytes only. */
#include "stage315_corner_patch.h"
#include "stage314_four_page_corner.h"
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
enum { LEN=FOJ_BC1_PAGE_RGBA_BYTES, EDGE=256 };
static const uint8_t colors[4][4]={
    {255,0,0,0},{0,255,0,64},{0,0,255,192},{255,255,255,255}
};
static void fill(uint8_t *p,const uint8_t rgba[4]) {
    for(size_t k=0;k<LEN;k+=4u)memcpy(p+k,rgba,4u);
}
static void transpose(const uint8_t *a,uint8_t *b) {
    for(unsigned y=0;y<EDGE;++y)for(unsigned x=0;x<EDGE;++x)
        memcpy(b+((size_t)x*EDGE+y)*4u,
               a+((size_t)y*EDGE+x)*4u,4u);
}
static void verify(void) {
    uint8_t *page[4]={0},*saved[4]={0};
    const uint8_t *p[4]={0};
    const size_t len[4]={LEN,LEN,LEN,LEN};
    uint8_t *patch=(uint8_t*)malloc(LEN);
    uint8_t *trans=(uint8_t*)malloc(LEN);
    uint8_t *other=(uint8_t*)malloc(LEN);
    assert(patch && trans && other);
    for(unsigned i=0;i<4u;++i) {
        page[i]=(uint8_t*)malloc(LEN);
        saved[i]=(uint8_t*)malloc(LEN);
        assert(page[i] && saved[i]);
        fill(page[i],colors[i]);
        memcpy(saved[i],page[i],LEN);
        p[i]=page[i];
    }
    FojStage315CornerReport r={0};
    assert(foj_stage315_build_corner_patch(p,len,patch,LEN,&r));
    assert(r.pixels_written==65536u && r.distinct_corner_pairs==6u);
    assert(r.strict_four_page_midpoint==1u);
    static const uint8_t center[4]={128,128,128,128};
    assert(memcmp(r.midpoint_rgba,center,4u)==0);
    for(unsigned y=0;y<EDGE;++y)for(unsigned x=0;x<EDGE;++x) {
        const unsigned corner=(y>=128u?2u:0u)+(x>=128u?1u:0u);
        assert(memcmp(patch+((size_t)y*EDGE+x)*4u,colors[corner],4u)==0);
    }
    /* 9x9 samples: compare Stage314 floating sampler to integer rational
       oracle, checking all RGBA channels and single final rounding. */
    for(unsigned yy=0;yy<=8u;++yy)for(unsigned xx=0;xx<=8u;++xx) {
        const float u=(511.5f+(float)xx/8.f)/1024.f;
        const float v=(511.5f+(float)yy/8.f)/1024.f;
        uint8_t got[4]={0};
        assert(foj_stage314_four_page_bilinear(
            p[0],LEN,p[1],LEN,p[2],LEN,p[3],LEN,u,v,got));
        for(unsigned k=0;k<4u;++k) {
            const unsigned q=colors[0][k]*(8u-xx)*(8u-yy)+
                             colors[1][k]*xx*(8u-yy)+
                             colors[2][k]*(8u-xx)*yy+
                             colors[3][k]*xx*yy;
            assert(got[k]==(uint8_t)((q+32u)/64u));
        }
    }
    transpose(patch,trans);
    const uint8_t *reordered[4]={p[0],p[2],p[1],p[3]};
    FojStage315CornerReport transpose_report={0};
    assert(foj_stage315_build_corner_patch(
        reordered,len,other,LEN,&transpose_report));
    assert(memcmp(other,trans,LEN)==0);
    assert(memcmp(transpose_report.midpoint_rgba,r.midpoint_rgba,4u)==0);
    memset(other,0xa5,LEN);
    FojStage315CornerReport guard={77u,88u,99u,{17,18,19,20}};
    const FojStage315CornerReport unchanged=guard;
    const size_t bad[4]={LEN,LEN-1u,LEN,LEN};
    assert(!foj_stage315_build_corner_patch(p,bad,other,LEN,&guard));
    assert(!foj_stage315_build_corner_patch(p,len,other,LEN-1u,&guard));
    assert(!foj_stage315_build_corner_patch(NULL,len,other,LEN,&guard));
    assert(!foj_stage315_build_corner_patch(p,NULL,other,LEN,&guard));
    assert(!foj_stage315_build_corner_patch(p,len,NULL,LEN,&guard));
    assert(!foj_stage315_build_corner_patch(p,len,other,LEN,NULL));
    const uint8_t *missing[4]={p[0],NULL,p[2],p[3]};
    assert(!foj_stage315_build_corner_patch(missing,len,other,LEN,&guard));
    for(unsigned i=0;i<4u;++i) {
        assert(!foj_stage315_build_corner_patch(p,len,page[i],LEN,&guard));
        assert(!foj_stage315_build_corner_patch(p,len,other,LEN,
             (FojStage315CornerReport*)(void*)(page[i]+16u)));
    }
    assert(!foj_stage315_build_corner_patch(p,len,other,LEN,
         (FojStage315CornerReport*)(void*)(other+16u)));
    assert(memcmp(&guard,&unchanged,sizeof(guard))==0);
    for(size_t n=0;n<LEN;++n)assert(other[n]==0xa5);
    for(unsigned i=0;i<4u;++i)assert(memcmp(page[i],saved[i],LEN)==0);
    for(unsigned i=0;i<4u;++i)fill(page[i],colors[0]);
    assert(foj_stage315_build_corner_patch(p,len,patch,LEN,&r));
    assert(r.pixels_written==65536u && r.distinct_corner_pairs==0u);
    assert(r.strict_four_page_midpoint==0u);
    assert(memcmp(r.midpoint_rgba,colors[0],4u)==0);
    for(size_t k=0;k<LEN;k+=4u)
        assert(memcmp(patch+k,colors[0],4u)==0);
    for(unsigned i=0;i<4u;++i){free(page[i]);free(saved[i]);}
    free(patch);free(trans);free(other);
    puts("STAGE315_NATIVE_FOUR_PAGE_65536_PIXELS_81_UVS_PASS");
}
int main(void){verify();return 0;}
