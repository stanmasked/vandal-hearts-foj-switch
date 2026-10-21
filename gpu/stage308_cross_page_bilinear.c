#include "stage308_cross_page_bilinear.h"
#include <math.h>
#include <stddef.h>
#include <string.h>

/* Both page edges use generated Stage301 C-decoded RGBA buffers. We refuse
 * negative/NaN/inf UV, other pages, and mismatched page ranges. */
int foj_stage308_cross_page_bilinear(
    const uint8_t *left_rgba, size_t left_bytes,
    const uint8_t *right_rgba, size_t right_bytes,
    unsigned row_y, float atlas_u, uint8_t out_rgba[4]) {
    if (!left_rgba || !right_rgba || !out_rgba ||
        left_bytes!=FOJ_BC1_PAGE_RGBA_BYTES ||
        right_bytes!=FOJ_BC1_PAGE_RGBA_BYTES ||
        row_y>=FOJ_BC1_PAGE_EDGE || !isfinite(atlas_u))
        return 0;
    const float first=511.5f/1024.f;
    const float last=512.5f/1024.f;
    if (atlas_u<first || atlas_u>last)return 0;
    /* 2 samples at distinct pages; t=0 at original texel center 511,
     * t=1 at 512, exactly 0.5 at normalized atlas u=0.5. */
    const float t=atlas_u*1024.f-511.5f;
    if (t<0.f || t>1.f)return 0;
    FojBc1PageUv a={0},b={0};
    if (!foj_bc1_1024_resolve_texel(511u,256u+row_y,&a) ||
        !foj_bc1_1024_resolve_texel(512u,256u+row_y,&b) ||
        a.page_x!=1u || a.page_y!=1u || a.local_x!=255u ||
        b.page_x!=2u || b.page_y!=1u || b.local_x!=0u ||
        a.local_y!=row_y || b.local_y!=row_y)
        return 0;
    const size_t at_left=((size_t)row_y*256u+255u)*4u;
    const size_t at_right=(size_t)row_y*256u*4u;
    uint8_t mixed[4];
    for (unsigned channel=0;channel<4u;++channel) {
        const float value=(1.f-t)*left_rgba[at_left+channel]+
                          t*right_rgba[at_right+channel];
        /* All inputs are 0..255, so rounding cannot overflow. */
        mixed[channel]=(uint8_t)floorf(value+0.5f);
    }
    memcpy(out_rgba,mixed,4u);
    return 1;
}

int foj_stage308_requires_two_pages(
    const uint8_t left_pixel[4], const uint8_t right_pixel[4],
    const uint8_t blended_pixel[4]) {
    if (!left_pixel || !right_pixel || !blended_pixel)return 0;
    int differs=0,strict_interior=0;
    for (unsigned k=0;k<4u;++k) {
        const int a=left_pixel[k],b=right_pixel[k],m=blended_pixel[k];
        if (a!=b)differs=1;
        const int lower=a<b?a:b,upper=a>b?a:b;
        if (m<lower || m>upper)return 0;
        if (m>lower && m<upper)strict_interior=1;
    }
    return differs && strict_interior &&
        memcmp(left_pixel,blended_pixel,4u)!=0 &&
        memcmp(right_pixel,blended_pixel,4u)!=0;
}
