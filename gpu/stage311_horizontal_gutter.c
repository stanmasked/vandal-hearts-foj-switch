#include "stage311_horizontal_gutter.h"
#include "stage303_bc1_page_uv.h"
#include <math.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>

static int overlaps(const void *aa,size_t na,const void *bb,size_t nb) {
    const uintptr_t a=(uintptr_t)aa,b=(uintptr_t)bb;
    if (na>UINTPTR_MAX-a || nb>UINTPTR_MAX-b)return 1;
    return a<b+nb && b<a+na;
}
static int valid(const uint8_t *top,size_t top_bytes,
                 const uint8_t *bottom,size_t bottom_bytes) {
    return top && bottom &&
        top_bytes==FOJ_BC1_PAGE_RGBA_BYTES &&
        bottom_bytes==FOJ_BC1_PAGE_RGBA_BYTES;
}

int foj_stage311_horizontal_bilinear(
    const uint8_t *top,size_t top_bytes,
    const uint8_t *bottom,size_t bottom_bytes,
    unsigned local_x,float atlas_v,uint8_t out[4]) {
    if (!valid(top,top_bytes,bottom,bottom_bytes) || !out ||
        local_x>=FOJ_BC1_PAGE_EDGE || !isfinite(atlas_v))
        return 0;
    const float lower=511.5f/1024.f,upper=512.5f/1024.f;
    if (atlas_v<lower || atlas_v>upper)return 0;
    const float t=atlas_v*1024.f-511.5f;
    if (t<0.f || t>1.f)return 0;
    FojBc1PageUv up={0},down={0};
    if (!foj_bc1_1024_resolve_texel(256u+local_x,511u,&up) ||
        !foj_bc1_1024_resolve_texel(256u+local_x,512u,&down) ||
        up.page_x!=1u || up.page_y!=1u ||
        down.page_x!=1u || down.page_y!=2u ||
        up.local_x!=local_x || up.local_y!=255u ||
        down.local_x!=local_x || down.local_y!=0u)
        return 0;
    const size_t a=((size_t)255u*256u+local_x)*4u;
    const size_t b=(size_t)local_x*4u;
    uint8_t temp[4];
    for (unsigned k=0;k<4u;++k)
        temp[k]=(uint8_t)floorf(
            (1.f-t)*top[a+k]+t*bottom[b+k]+.5f);
    memcpy(out,temp,4u);
    return 1;
}

int foj_stage311_build_horizontal_gutter(
    const uint8_t *top,size_t top_bytes,
    const uint8_t *bottom,size_t bottom_bytes,
    uint8_t *gutter,size_t gutter_bytes,
    FojStage311HorizontalReport *report) {
    if (!valid(top,top_bytes,bottom,bottom_bytes) ||
        !gutter || !report ||
        gutter_bytes!=FOJ_BC1_PAGE_RGBA_BYTES ||
        overlaps(gutter,gutter_bytes,top,top_bytes) ||
        overlaps(gutter,gutter_bytes,bottom,bottom_bytes) ||
        overlaps(gutter,gutter_bytes,report,sizeof(*report)) ||
        overlaps(report,sizeof(*report),top,top_bytes) ||
        overlaps(report,sizeof(*report),bottom,bottom_bytes))
        return 0;
    uint8_t *tmp=(uint8_t*)malloc(FOJ_BC1_PAGE_RGBA_BYTES);
    if (!tmp)return 0;
    FojStage311HorizontalReport result={0};
    int ok=1;
    for (unsigned x=0;x<256u;++x) {
        const uint8_t *a=top+((size_t)255u*256u+x)*4u;
        const uint8_t *b=bottom+(size_t)x*4u;
        uint8_t mid[4]={0};
        if (!foj_stage311_horizontal_bilinear(
                top,top_bytes,bottom,bottom_bytes,x,.5f,mid)) {
            ok=0;
            break;
        }
        ++result.columns_processed;
        if (memcmp(a,b,4u))++result.contrasting_columns;
        int inside=0,within=1;
        for(unsigned k=0;k<4u;++k) {
            const int lo=a[k]<b[k]?a[k]:b[k];
            const int hi=a[k]>b[k]?a[k]:b[k];
            if (mid[k]<lo || mid[k]>hi)within=0;
            if (mid[k]>lo && mid[k]<hi)inside=1;
        }
        if (inside && within && memcmp(mid,a,4u) &&
            memcmp(mid,b,4u))++result.genuinely_mixed_columns;
        for (unsigned y=0;y<256u;++y)
            memcpy(tmp+((size_t)y*256u+x)*4u,y<128u?a:b,4u);
    }
    if (ok && result.columns_processed==256u) {
        memcpy(gutter,tmp,FOJ_BC1_PAGE_RGBA_BYTES);
        *report=result;
    }else ok=0;
    free(tmp);
    return ok;
}
