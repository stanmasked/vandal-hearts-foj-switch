#include "stage335_source_staging.h"
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <stdio.h>
#include <assert.h>

static FojStage332DdsInfo info(unsigned w,unsigned h,unsigned mip,FojStage332Format format){
    FojStage332DdsInfo d={w,h,mip,format,(size_t)w*h*4u};
    return d;
}
static void odd_width_padding(void){
    FojStage332DdsInfo d=info(74u,81u,1u,FOJ_STAGE332_BGR8);
    FojStage335SourceStagingPlan p={0};
    const size_t pixels=(size_t)d.width*d.height*4u;
    uint8_t *src=malloc(pixels),*dst=malloc(81u*320u+128u);
    assert(src&&dst);
    for(size_t i=0;i<pixels;++i)src[i]=(uint8_t)(i*29u+11u);
    memset(dst,0xaa,81u*320u+128u);
    assert(foj_stage335_make_source_staging_plan(&d,pixels,81u*320u,64u,&p));
    assert(p.width==74u&&p.height==81u&&p.row_pitch_bytes==320u&&
           p.row_length_pixels==80u&&p.staging_bytes==81u*320u);
    assert(foj_stage335_stage_source_rgba(&d,&p,src,pixels,dst,81u*320u,64u));
    for(unsigned y=0;y<81u;++y){
        assert(memcmp(dst+y*320u,src+y*74u*4u,74u*4u)==0);
        for(unsigned x=74u*4u;x<320u;++x)assert(dst[y*320u+x]==0u);
    }
    for(size_t x=81u*320u;x<81u*320u+128u;++x)assert(dst[x]==0xaa);
    free(src);free(dst);
}
static void refuse_without_mutation(void){
    FojStage332DdsInfo d=info(8u,8u,1u,FOJ_STAGE332_BC1);
    FojStage335SourceStagingPlan plan={0};
    unsigned char src[256]={0},dst[320];
    memset(dst,0x7e,sizeof(dst));
    /* A short destination must be rejected before any data is touched. */
    FojStage335SourceStagingPlan sentinel={99u,77u,55u,44u,33u,22u};
    FojStage335SourceStagingPlan same=sentinel;
    assert(!foj_stage335_make_source_staging_plan(&d,256u,320u,64u,&same));
    assert(memcmp(&same,&sentinel,sizeof(same))==0);
    assert(!foj_stage335_make_source_staging_plan(&d,255u,1024u,64u,&same));
    assert(!foj_stage335_make_source_staging_plan(&d,256u,1024u,3u,&same));
    assert(!foj_stage335_make_source_staging_plan(&d,256u,1024u,8192u,&same));
    FojStage332DdsInfo wrong=d;wrong.rgba_bytes++;
    assert(!foj_stage335_make_source_staging_plan(&wrong,256u,1024u,64u,&same));
    wrong=d;wrong.width=2049u;
    assert(!foj_stage335_make_source_staging_plan(&wrong,256u,1024u,64u,&same));
    wrong=d;wrong.format=(FojStage332Format)99;
    assert(!foj_stage335_make_source_staging_plan(&wrong,256u,1024u,64u,&same));
    assert(memcmp(&same,&sentinel,sizeof(same))==0);
    assert(!foj_stage335_stage_source_rgba(&d,&sentinel,src,256u,dst,320u,64u));
    for(size_t i=0;i<sizeof(dst);++i)assert(dst[i]==0x7e);
    /* Now build a valid plan against a sufficiently large destination. */
    uint8_t dest[640];memset(dest,0xc7,sizeof(dest));
    assert(foj_stage335_make_source_staging_plan(&d,256u,640u,64u,&plan));
    FojStage335SourceStagingPlan forged=plan;forged.staging_bytes-=1u;
    assert(!foj_stage335_stage_source_rgba(&d,&forged,src,256u,dest,640u,64u));
    assert(!foj_stage335_stage_source_rgba(&d,&plan,src,256u,dest,511u,64u));
    /* Destination begins inside source allocation: overlap must be rejected. */
    uint8_t overlap[1024];memset(overlap,0xd0,sizeof(overlap));
    assert(!foj_stage335_stage_source_rgba(&d,&plan,overlap,256u,overlap+12u,1012u,64u));
    for(size_t i=0;i<sizeof(overlap);++i)assert(overlap[i]==0xd0);
    for(size_t i=0;i<sizeof(dest);++i)assert(dest[i]==0xc7);
}
static void full_extent(void){
    FojStage332DdsInfo d=info(2048u,2048u,12u,FOJ_STAGE332_BGRA8);
    const size_t bytes=(size_t)2048u*2048u*4u;
    FojStage335SourceStagingPlan p={0};
    assert(foj_stage335_make_source_staging_plan(&d,bytes,bytes,4096u,&p));
    assert(p.row_pitch_bytes==8192u&&p.row_length_pixels==2048u&&
           p.staging_bytes==bytes);
    uint8_t *src=malloc(bytes),*dst=malloc(bytes);
    assert(src&&dst);
    memset(src,0x12,bytes);memset(dst,0x5f,bytes);
    assert(foj_stage335_stage_source_rgba(&d,&p,src,bytes,dst,bytes,4096u));
    assert(memcmp(src,dst,bytes)==0);
    free(src);free(dst);
}
int main(void){
    odd_width_padding();refuse_without_mutation();full_extent();
    puts("STAGE335_SYNTHETIC_BOUNDED_RGBA_STAGING_PASS");return 0;
}
