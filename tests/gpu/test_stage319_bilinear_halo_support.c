/* Stage319: synthetic bilinear texel halo around UV triangle coverage.
 * No game meshes, no original PS3 resources, no GPU claims. */
#include "stage319_bilinear_halo_support.h"
#include <assert.h>
#include <math.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

static FojStage318Triangle triangle(float u0,float v0,float u1,float v1,
                                    float u2,float v2) {
    const FojStage318Triangle t={{{u0,v0},{u1,v1},{u2,v2}}};
    return t;
}
static uint16_t bit(unsigned x,unsigned y) {
    return (uint16_t)(1u<<(y*4u+x));
}
static unsigned count(uint16_t mask) {
    unsigned n=0u;
    for(unsigned i=0u;i<16u;++i)n+=(mask>>i)&1u;
    return n;
}
static FojStage319FilterSupport verify(
    const FojStage318Triangle *tri,uint16_t geom,uint16_t filter) {
    FojStage319FilterSupport out={0};
    assert(foj_stage319_triangle_bilinear_pages(tri,&out));
    assert(out.geometry_page_mask==geom);
    assert(out.filter_page_mask==filter);
    assert(out.halo_only_page_mask==(uint16_t)(filter&~geom));
    assert(out.geometry_pages==count(geom));
    assert(out.filter_pages==count(filter));
    assert(out.halo_only_pages==count((uint16_t)(filter&~geom)));
    assert(out.filter_halo_uv==1.0/2048.0);
    return out;
}
static void all_page_interiors(void) {
    for(unsigned py=0;py<4u;++py)
      for(unsigned px=0;px<4u;++px) {
        const float x=px/4.f,y=py/4.f;
        const FojStage318Triangle t=triangle(
            x+.08f,y+.09f,x+.13f,y+.09f,x+.08f,y+.14f);
        verify(&t,bit(px,py),bit(px,py));
      }
}
static void nearby_vertical_horizontal(void) {
    for(unsigned y=0;y<4u;++y)
      for(unsigned x=1;x<4u;++x) {
        const float line=x/4.f,row=y/4.f;
        const FojStage318Triangle near=triangle(
            line-.00040f,row+.08f,
            line-.00012f,row+.08f,
            line-.00040f,row+.14f);
        const uint16_t west=bit(x-1u,y),east=bit(x,y);
        verify(&near,west,(uint16_t)(west|east));
        const FojStage318Triangle far=triangle(
            line-.003f,row+.08f,
            line-.002f,row+.08f,
            line-.003f,row+.14f);
        verify(&far,west,west);
      }
    for(unsigned y=1;y<4u;++y)
      for(unsigned x=0;x<4u;++x) {
        const float line=y/4.f,col=x/4.f;
        const FojStage318Triangle near=triangle(
            col+.08f,line-.00040f,
            col+.14f,line-.00040f,
            col+.08f,line-.00012f);
        const uint16_t north=bit(x,y-1u),south=bit(x,y);
        verify(&near,north,(uint16_t)(north|south));
      }
}
static void all_nine_corner_halos(void) {
    unsigned cases=0;
    for(unsigned y=1u;y<4u;++y)for(unsigned x=1u;x<4u;++x) {
        const float u=x/4.f,v=y/4.f;
        const FojStage318Triangle inside_nw=triangle(
            u-.00040f,v-.00040f,
            u-.00010f,v-.00040f,
            u-.00040f,v-.00010f);
        const uint16_t nw=bit(x-1u,y-1u);
        const uint16_t all=(uint16_t)(
            nw|bit(x,y-1u)|bit(x-1u,y)|bit(x,y));
        verify(&inside_nw,nw,all);
        const FojStage318Triangle diagonal=triangle(
            u-.02f,v-.02f,u+.02f,v-.02f,u-.02f,v+.02f);
        const uint16_t three=(uint16_t)(
            nw|bit(x,y-1u)|bit(x-1u,y));
        verify(&diagonal,three,all);
        ++cases;
    }
    assert(cases==9u);
}
static void exact_boundary_touch(void) {
    /* Geometry has zero area on east page but its interpolated texels
     * touch that page across the half-texel support region. */
    const FojStage318Triangle t=triangle(
        .49f,.36f,.5f,.36f,.49f,.41f);
    const uint16_t geom=bit(1u,1u),filter=(uint16_t)(geom|bit(2u,1u));
    verify(&t,geom,filter);
}
static void outer_clamp(void) {
    const FojStage318Triangle lower=triangle(
        .00001f,.00001f,.002f,.00001f,.00001f,.002f);
    verify(&lower,bit(0u,0u),bit(0u,0u));
    const FojStage318Triangle upper=triangle(
        .999f,.999f,1.f,.999f,.999f,1.f);
    verify(&upper,bit(3u,3u),bit(3u,3u));
}
static void transpose_equivalence(void) {
    for(unsigned y=1u;y<4u;++y)for(unsigned x=1u;x<4u;++x) {
        const float u=x/4.f,v=y/4.f;
        const FojStage318Triangle t=triangle(
            u-.00035f,v-.00042f,
            u-.00012f,v-.00042f,
            u-.00035f,v-.00014f);
        FojStage318Triangle transposed=t;
        for(unsigned i=0u;i<3u;++i) {
            transposed.point[i].u=t.point[i].v;
            transposed.point[i].v=t.point[i].u;
        }
        FojStage319FilterSupport original={0},b={0};
        assert(foj_stage319_triangle_bilinear_pages(&t,&original));
        assert(foj_stage319_triangle_bilinear_pages(&transposed,&b));
        for(unsigned py=0u;py<4u;++py)
          for(unsigned px=0u;px<4u;++px) {
            const unsigned aa=py*4u+px,bb=px*4u+py;
            assert(((original.geometry_page_mask>>aa)&1u)==
                   ((b.geometry_page_mask>>bb)&1u));
            assert(((original.filter_page_mask>>aa)&1u)==
                   ((b.filter_page_mask>>bb)&1u));
          }
    }
}
static void reject_atomic(void) {
    FojStage318Triangle t=triangle(.1f,.1f,.2f,.1f,.1f,.2f);
    FojStage319FilterSupport out;
    memset(&out,0x5a,sizeof(out));
    const FojStage319FilterSupport saved=out;
    assert(!foj_stage319_triangle_bilinear_pages(NULL,&out));
    assert(!foj_stage319_triangle_bilinear_pages(&t,NULL));
    assert(!foj_stage319_triangle_bilinear_pages(
        &t,(FojStage319FilterSupport*)(void*)&t));
    t.point[0].u=NAN;
    assert(!foj_stage319_triangle_bilinear_pages(&t,&out));
    t.point[0].u=INFINITY;
    assert(!foj_stage319_triangle_bilinear_pages(&t,&out));
    t.point[0].u=-.1f;
    assert(!foj_stage319_triangle_bilinear_pages(&t,&out));
    t.point[0].u=1.01f;
    assert(!foj_stage319_triangle_bilinear_pages(&t,&out));
    t=triangle(.1f,.1f,.2f,.2f,.3f,.3f);
    assert(!foj_stage319_triangle_bilinear_pages(&t,&out));
    assert(memcmp(&out,&saved,sizeof(out))==0);
}
int main(void) {
    all_page_interiors();
    nearby_vertical_horizontal();
    all_nine_corner_halos();
    exact_boundary_touch();
    outer_clamp();
    transpose_equivalence();
    reject_atomic();
    puts("STAGE319_NATIVE_BILINEAR_HALF_TEXEL_FILTER_PAGE_SUPPORT_PASS");
    return 0;
}
