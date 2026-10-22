#include "stage325_corner_tile_partition.h"
#include <assert.h>
#include <math.h>
#include <stdint.h>
#include <stdio.h>

typedef struct { double u, v; } Point2;

static uint64_t rng_state=UINT64_C(0x8f31a2c7d45e690b);
static uint64_t next_u64(void) {
    uint64_t x=rng_state;
    x^=x>>12;
    x^=x<<25;
    x^=x>>27;
    rng_state=x;
    return x*UINT64_C(2685821657736338717);
}
static double unit(void) {
    return ((double)(next_u64()>>11)+0.5)*(1.0/9007199254740992.0);
}
static FojStage325Vertex vertex(float u,float v) {
    FojStage325Vertex p={2.0f*u+v,-u+3.0f*v,.5f+u-v,u,v};
    return p;
}
static double cross2(double ax,double ay,double bx,double by,
                     double px,double py) {
    return (bx-ax)*(py-ay)-(by-ay)*(px-ax);
}
static double tri_area2(const FojStage325Vertex *a,
                        const FojStage325Vertex *b,
                        const FojStage325Vertex *c) {
    return cross2(a->u,a->v,b->u,b->v,c->u,c->v);
}
static int triangle_contains(const FojStage325Vertex *a,
                             const FojStage325Vertex *b,
                             const FojStage325Vertex *c,
                             double u,double v) {
    const double area=tri_area2(a,b,c);
    if(fabs(area)<1e-24)return 0;
    const double ab=cross2(a->u,a->v,b->u,b->v,u,v);
    const double bc=cross2(b->u,b->v,c->u,c->v,u,v);
    const double ca=cross2(c->u,c->v,a->u,a->v,u,v);
    return area>0.0 ? ab>=0.0&&bc>=0.0&&ca>=0.0
                    : ab<=0.0&&bc<=0.0&&ca<=0.0;
}
static int point_on_segment(double u,double v,
                            const FojStage325Vertex *a,
                            const FojStage325Vertex *b) {
    const double cross=cross2(a->u,a->v,b->u,b->v,u,v);
    if(fabs(cross)>1e-12)return 0;
    const double dot=(u-a->u)*(u-b->u)+(v-a->v)*(v-b->v);
    return dot<=1e-12;
}
static int near_soup_edge(const FojStage325Vertex *soup,unsigned n,
                          double u,double v) {
    for(unsigned i=0u;i<n;i+=3u) {
        const FojStage325Vertex *a=soup+i,*b=soup+i+1u,*c=soup+i+2u;
        if(point_on_segment(u,v,a,b)||point_on_segment(u,v,b,c)||
           point_on_segment(u,v,c,a))return 1;
    }
    return 0;
}
static unsigned soup_hits(const FojStage325Vertex *soup,unsigned n,
                          double u,double v) {
    unsigned hits=0u;
    assert(n%3u==0u);
    for(unsigned i=0u;i<n;i+=3u)
        if(triangle_contains(soup+i,soup+i+1u,soup+i+2u,u,v))++hits;
    return hits;
}
static Point2 sample_source_triangle(const FojStage325Triangle *t) {
    double a=unit(),b=unit();
    if(a+b>1.0){a=1.0-a;b=1.0-b;}
    const double u0=t->point[0].u,v0=t->point[0].v;
    const double u1=t->point[1].u,v1=t->point[1].v;
    const double u2=t->point[2].u,v2=t->point[2].v;
    Point2 p={u0+a*(u1-u0)+b*(u2-u0),
              v0+a*(v1-v0)+b*(v2-v0)};
    return p;
}
static void verify_coverage(const FojStage325Triangle *t,unsigned px,unsigned py,
                            unsigned requested_samples) {
    FojStage325Vertex tile[FOJ_STAGE325_TILE_VERTICES];
    FojStage325Vertex remainder[FOJ_STAGE325_REMAINDER_VERTICES];
    FojStage325PartitionReport report={0};
    assert(foj_stage325_partition_triangle_at_corner_tile(
        t,px,py,tile,FOJ_STAGE325_TILE_VERTICES,
        remainder,FOJ_STAGE325_REMAINDER_VERTICES,&report));

    const double left=((double)px*256.0-8.0)/1024.0;
    const double right=((double)px*256.0+8.0)/1024.0;
    const double top=((double)py*256.0-8.0)/1024.0;
    const double bottom=((double)py*256.0+8.0)/1024.0;
    unsigned accepted=0u;
    for(unsigned attempt=0u;accepted<requested_samples&&
        attempt<requested_samples*8u;++attempt) {
        double a=unit(),b=unit();
        if(a+b>1.0){a=1.0-a;b=1.0-b;}
        /* Avoid the source triangle's own boundary so point location is strict. */
        if(a<1e-8||b<1e-8||a+b>1.0-1e-8)continue;
        const Point2 p=sample_source_triangle(t);
        const double u=p.u,v=p.v;
        if(fabs(u-left)<1e-12||fabs(u-right)<1e-12||
           fabs(v-top)<1e-12||fabs(v-bottom)<1e-12)continue;
        const double local_u=(u-left)/(right-left);
        const double local_v=(v-top)/(bottom-top);
        if(near_soup_edge(tile,report.tile_vertices,local_u,local_v)||
           near_soup_edge(remainder,report.remainder_vertices,u,v))continue;

        const unsigned tile_hits=soup_hits(
            tile,report.tile_vertices,local_u,local_v);
        const unsigned remainder_hits=soup_hits(
            remainder,report.remainder_vertices,u,v);
        const int inside_tile=u>left&&u<right&&v>top&&v<bottom;
        assert(tile_hits==(inside_tile?1u:0u));
        assert(remainder_hits==(inside_tile?0u:1u));
        assert(tile_hits+remainder_hits==1u);
        ++accepted;
    }
    assert(accepted==requested_samples);
}
static FojStage325Triangle around_tile(unsigned px,unsigned py) {
    const float cx=(float)px*.25f,cy=(float)py*.25f;
    FojStage325Triangle t={{
        vertex(cx-.1f,cy-.1f),vertex(cx+.1f,cy-.1f),vertex(cx,cy+.1f)
    }};
    return t;
}
static FojStage325Triangle random_near_tile(unsigned px,unsigned py) {
    const double cx=(double)px*.25,cy=(double)py*.25;
    const double low_u=cx-.17,high_u=cx+.17;
    const double low_v=cy-.17,high_v=cy+.17;
    for(unsigned tries=0u;tries<1000u;++tries) {
        FojStage325Triangle t={{
            vertex((float)(low_u+unit()*(high_u-low_u)),
                   (float)(low_v+unit()*(high_v-low_v))),
            vertex((float)(low_u+unit()*(high_u-low_u)),
                   (float)(low_v+unit()*(high_v-low_v))),
            vertex((float)(low_u+unit()*(high_u-low_u)),
                   (float)(low_v+unit()*(high_v-low_v)))
        }};
        if(fabs(tri_area2(t.point,t.point+1u,t.point+2u))>1e-5)return t;
    }
    assert(!"unable to generate a non-degenerate synthetic triangle");
    return around_tile(px,py);
}
static void all_nine_junctions(void) {
    const FojStage325Triangle broad_a={{
        vertex(0.0f,0.0f),vertex(1.0f,0.0f),vertex(0.0f,1.0f)
    }};
    const FojStage325Triangle broad_b={{
        vertex(1.0f,1.0f),vertex(1.0f,0.0f),vertex(0.0f,1.0f)
    }};
    unsigned cases=0u;
    for(unsigned py=1u;py<=3u;++py)for(unsigned px=1u;px<=3u;++px) {
        const FojStage325Triangle centered=around_tile(px,py);
        verify_coverage(&centered,px,py,4096u);
        verify_coverage(&broad_a,px,py,1024u);
        verify_coverage(&broad_b,px,py,1024u);
        ++cases;
        for(unsigned i=0u;i<56u;++i) {
            const FojStage325Triangle t=random_near_tile(px,py);
            verify_coverage(&t,px,py,192u);
            ++cases;
        }
    }
    assert(cases==9u*(1u+2u+56u));
    printf("STAGE326_PARTITION_SPATIAL_COVERAGE_PASS cases=%u\n",cases);
}
int main(void) {
    all_nine_junctions();
    return 0;
}
