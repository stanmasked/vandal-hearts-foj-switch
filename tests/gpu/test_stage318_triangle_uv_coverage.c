/* Stage318 pure native exact UV triangle atlas coverage regression.
 * All coordinates synthetic, no original PS3 source material. */
#include "stage318_triangle_uv_coverage.h"
#include <assert.h>
#include <math.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

static FojStage318Triangle tri(float u0,float v0,float u1,float v1,
                               float u2,float v2) {
    const FojStage318Triangle t={{{u0,v0},{u1,v1},{u2,v2}}};
    return t;
}
static uint16_t bit(unsigned px,unsigned py) {
    return (uint16_t)(1u<<(py*4u+px));
}
static void check(const FojStage318Triangle *t,uint16_t expected,
                  unsigned xlines,unsigned ylines) {
    FojStage318Coverage c={0};
    assert(foj_stage318_triangle_page_coverage(t,&c));
    assert(c.page_mask==expected);
    assert(c.vertical_page_boundaries_crossed==xlines);
    assert(c.horizontal_page_boundaries_crossed==ylines);
    assert(c.triangle_area_uv>0.0);
    assert(fabs(c.covered_area_uv-c.triangle_area_uv)<1e-9);
    unsigned count=0;
    double sum=0.0;
    for(unsigned p=0u;p<16u;++p) {
        if(expected&(1u<<p)) {
            assert(c.page_area_uv[p]>0.0);
            ++count;
        } else assert(c.page_area_uv[p]==0.0);
        sum+=c.page_area_uv[p];
    }
    assert(c.pages_covered==count);
    assert(fabs(sum-c.triangle_area_uv)<1e-9);
}
static void each_page(void) {
    for(unsigned py=0u;py<4u;++py)
      for(unsigned px=0u;px<4u;++px) {
        const float u=(float)px/4.f,v=(float)py/4.f;
        const FojStage318Triangle t=
            tri(u+.02f,v+.03f,u+.09f,v+.03f,u+.02f,v+.11f);
        check(&t,bit(px,py),0u,0u);
        /* Cyclic permutations must preserve the exact per-page areas. */
        const FojStage318Triangle shifted=
            tri(t.point[1].u,t.point[1].v,t.point[2].u,t.point[2].v,
                t.point[0].u,t.point[0].v);
        FojStage318Coverage a={0},b={0};
        assert(foj_stage318_triangle_page_coverage(&t,&a));
        assert(foj_stage318_triangle_page_coverage(&shifted,&b));
        assert(a.page_mask==b.page_mask);
        for(unsigned i=0;i<16u;++i)
            assert(fabs(a.page_area_uv[i]-b.page_area_uv[i])<1e-10);
      }
}
static void nine_four_way_junctions(void) {
    unsigned tested=0u;
    for(unsigned py=1u;py<4u;++py)
      for(unsigned px=1u;px<4u;++px) {
        const float x=(float)px/4.f,y=(float)py/4.f;
        const FojStage318Triangle t=tri(
            x-.05f,y-.05f,x+.05f,y-.05f,x,y+.15f);
        const uint16_t expected=
            (uint16_t)(bit(px-1u,py-1u)|bit(px,py-1u)|
                       bit(px-1u,py)|bit(px,py));
        check(&t,expected,1u,1u);
        FojStage318Coverage a={0};
        assert(foj_stage318_triangle_page_coverage(&t,&a));
        assert(a.pages_covered==4u);
        ++tested;
      }
    assert(tested==9u);
}
static void straight_seams(void) {
    for(unsigned px=1u;px<4u;++px) {
        const float x=(float)px/4.f;
        FojStage318Triangle t=tri(
            x-.03f,.36f,x+.03f,.36f,x-.03f,.42f);
        check(&t,(uint16_t)(bit(px-1u,1u)|bit(px,1u)),1u,0u);
    }
    for(unsigned py=1u;py<4u;++py) {
        const float y=(float)py/4.f;
        FojStage318Triangle t=tri(
            .36f,y-.03f,.42f,y-.03f,.36f,y+.03f);
        check(&t,(uint16_t)(bit(1u,py-1u)|bit(1u,py)),0u,1u);
    }
}
static void bbox_is_not_triangle_coverage(void) {
    /* The bounding rectangle overlaps SE but triangle x+y<=1 has no
     * positive area there: exact polygon clipping must reject that page. */
    const FojStage318Triangle t=
        tri(.48f,.48f,.52f,.48f,.48f,.52f);
    check(&t,(uint16_t)(bit(1u,1u)|bit(2u,1u)|bit(1u,2u)),1u,1u);
    /* Exactly touching a page boundary with no area on its far side. */
    const FojStage318Triangle touch=
        tri(.50f,.36f,.59f,.36f,.50f,.42f);
    check(&touch,bit(2u,1u),0u,0u);
}
static void transpose_equivalence(void) {
    /* Transform every genuine four-way junction and verify the entire
     * 16-cell coverage area array transforms with it. */
    for(unsigned py=1u;py<4u;++py)
      for(unsigned px=1u;px<4u;++px) {
        const float x=(float)px/4.f,y=(float)py/4.f;
        const FojStage318Triangle t=tri(
            x-.043f,y-.06f,x+.07f,y-.04f,x-.01f,y+.11f);
        FojStage318Triangle swapped=t;
        for(unsigned i=0;i<3u;++i) {
            swapped.point[i].u=t.point[i].v;
            swapped.point[i].v=t.point[i].u;
        }
        FojStage318Coverage a={0},b={0};
        assert(foj_stage318_triangle_page_coverage(&t,&a));
        assert(foj_stage318_triangle_page_coverage(&swapped,&b));
        assert(a.pages_covered==b.pages_covered);
        assert(a.vertical_page_boundaries_crossed==
               b.horizontal_page_boundaries_crossed);
        assert(a.horizontal_page_boundaries_crossed==
               b.vertical_page_boundaries_crossed);
        assert(fabs(a.triangle_area_uv-b.triangle_area_uv)<1e-10);
        for(unsigned j=0;j<4u;++j)
            for(unsigned i=0;i<4u;++i)
                assert(fabs(a.page_area_uv[j*4u+i]-
                            b.page_area_uv[i*4u+j])<1e-10);
      }
}
static void invalid_atomic(void) {
    FojStage318Triangle t=tri(.15f,.15f,.2f,.15f,.15f,.2f);
    FojStage318Coverage out={0};
    memset(&out,0xa5,sizeof(out));
    const FojStage318Coverage saved=out;
    assert(!foj_stage318_triangle_page_coverage(NULL,&out));
    assert(!foj_stage318_triangle_page_coverage(&t,NULL));
    assert(!foj_stage318_triangle_page_coverage(
        &t,(FojStage318Coverage*)(void*)&t));
    const FojStage318Triangle original=t;
    t.point[0].u=NAN;
    assert(!foj_stage318_triangle_page_coverage(&t,&out));
    t.point[0].u=INFINITY;
    assert(!foj_stage318_triangle_page_coverage(&t,&out));
    t.point[0].u=-0.01f;
    assert(!foj_stage318_triangle_page_coverage(&t,&out));
    t.point[0].u=1.01f;
    assert(!foj_stage318_triangle_page_coverage(&t,&out));
    t=tri(.1f,.1f,.2f,.2f,.3f,.3f);
    assert(!foj_stage318_triangle_page_coverage(&t,&out));
    t=tri(.1f,.1f,.100001f,.1f,.1f,.100001f);
    assert(!foj_stage318_triangle_page_coverage(&t,&out));
    assert(memcmp(&saved,&out,sizeof(out))==0);
    t=original;
    assert(memcmp(&original,&t,sizeof(t))==0);
    /* UV=1 outer atlas endpoint belongs to page 3, not page 4. */
    t=tri(.90f,.90f,1.f,.90f,.90f,1.f);
    check(&t,bit(3u,3u),0u,0u);
}
int main(void) {
    each_page();
    nine_four_way_junctions();
    straight_seams();
    bbox_is_not_triangle_coverage();
    transpose_equivalence();
    invalid_atomic();
    puts("STAGE318_NATIVE_16_PAGE_UV_TRIANGLES_EXACT_COVERAGE_PASS");
    return 0;
}
