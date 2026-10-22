#include "stage325_corner_tile_partition.h"
#include <assert.h>
#include <math.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

static double signed_area2(const FojStage325Vertex *a,
                           const FojStage325Vertex *b,
                           const FojStage325Vertex *c) {
    return ((double)b->u-a->u)*((double)c->v-a->v)-
           ((double)b->v-a->v)*((double)c->u-a->u);
}
static double tri_area(const FojStage325Vertex *a,
                       const FojStage325Vertex *b,
                       const FojStage325Vertex *c) {
    return fabs(signed_area2(a,b,c))*0.5;
}
static double soup_area(const FojStage325Vertex *p,unsigned n) {
    double sum=0.0;
    assert(n%3u==0u);
    for(unsigned i=0u;i<n;i+=3u)sum+=tri_area(p+i,p+i+1u,p+i+2u);
    return sum;
}
static FojStage325Vertex vertex(float u,float v) {
    FojStage325Vertex p={2.0f*u+v,-u+3.0f*v,.5f+u-v,u,v};
    return p;
}
static FojStage325Triangle covering_triangle(unsigned px,unsigned py) {
    const float cx=(float)px*.25f,cy=(float)py*.25f;
    FojStage325Triangle t={{
        vertex(cx-.1f,cy-.1f),
        vertex(cx+.1f,cy-.1f),
        vertex(cx,cy+.1f)
    }};
    return t;
}
static void check_affine(const FojStage325Vertex *p,int tile,
                         unsigned px,unsigned py) {
    double u=p->u,v=p->v;
    if(tile) {
        u=((double)px*256.0-8.0)/1024.0+
          (double)p->u*(16.0/1024.0);
        v=((double)py*256.0-8.0)/1024.0+
          (double)p->v*(16.0/1024.0);
        assert(p->u>=0.0f&&p->u<=1.0f&&p->v>=0.0f&&p->v<=1.0f);
    }
    assert(fabs((double)p->x-(2.0*u+v))<2e-6);
    assert(fabs((double)p->y-(-u+3.0*v))<2e-6);
    assert(fabs((double)p->z-(.5+u-v))<2e-6);
}
static void run_partition(const FojStage325Triangle *t,unsigned px,unsigned py,
                          FojStage325Vertex *tile,FojStage325Vertex *rem,
                          FojStage325PartitionReport *r) {
    assert(foj_stage325_partition_triangle_at_corner_tile(
        t,px,py,tile,FOJ_STAGE325_TILE_VERTICES,
        rem,FOJ_STAGE325_REMAINDER_VERTICES,r));
    assert(r->tile_vertices<=FOJ_STAGE325_TILE_VERTICES);
    assert(r->remainder_vertices<=FOJ_STAGE325_REMAINDER_VERTICES);
    assert(r->tile_vertices%3u==0u&&r->remainder_vertices%3u==0u);
    assert(r->tile_triangles==r->tile_vertices/3u);
    assert(r->remainder_triangles==r->remainder_vertices/3u);
    assert(fabs(soup_area(tile,r->tile_vertices)*(16.0/1024.0)*(16.0/1024.0)
                -r->tile_uv_area)<2e-8);
    assert(fabs(soup_area(rem,r->remainder_vertices)
                -r->remainder_uv_area)<2e-8);
    assert(fabs(r->input_uv_area-r->tile_uv_area-r->remainder_uv_area)<5e-7);
    for(unsigned i=0u;i<r->tile_vertices;++i)check_affine(tile+i,1,px,py);
    for(unsigned i=0u;i<r->remainder_vertices;++i)check_affine(rem+i,0,px,py);
    for(unsigned i=r->tile_vertices;i<FOJ_STAGE325_TILE_VERTICES;++i) {
        const FojStage325Vertex zero={0};
        assert(memcmp(tile+i,&zero,sizeof(zero))==0);
    }
    for(unsigned i=r->remainder_vertices;i<FOJ_STAGE325_REMAINDER_VERTICES;++i) {
        const FojStage325Vertex zero={0};
        assert(memcmp(rem+i,&zero,sizeof(zero))==0);
    }
}
static void all_nine_corners(void) {
    for(unsigned py=1u;py<=3u;++py)for(unsigned px=1u;px<=3u;++px) {
        FojStage325Triangle t=covering_triangle(px,py);
        FojStage325Vertex tile[FOJ_STAGE325_TILE_VERTICES];
        FojStage325Vertex rem[FOJ_STAGE325_REMAINDER_VERTICES];
        FojStage325PartitionReport r={0};
        memset(tile,0xa5,sizeof(tile));memset(rem,0x5a,sizeof(rem));
        run_partition(&t,px,py,tile,rem,&r);
        assert(r.tile_intersects==1u&&r.tile_vertices==6u);
        assert(r.tile_triangles==2u&&r.remainder_vertices>0u);
        assert(r.atlas_first_x==px*256u-8u);
        assert(r.atlas_first_y==py*256u-8u);
        assert(fabs(r.tile_uv_area-(16.0/1024.0)*(16.0/1024.0))<1e-8);
        unsigned corners=0u;
        for(unsigned i=0u;i<r.tile_vertices;++i) {
            assert((tile[i].u==0.0f||tile[i].u==1.0f)&&
                   (tile[i].v==0.0f||tile[i].v==1.0f));
            corners|=1u<<((tile[i].v==1.0f?2u:0u)+
                          (tile[i].u==1.0f?1u:0u));
        }
        assert(corners==0x0fu);
        assert(r.reserved[0]==0u&&r.reserved[6]==0u);
    }
}
static void wholly_inside_and_outside(void) {
    const unsigned px=2u,py=2u;
    const float left=(float)(px*256u-8u)/1024.0f;
    const float top=(float)(py*256u-8u)/1024.0f;
    const float width=16.0f/1024.0f;
    FojStage325Triangle inside={{
        vertex(left+width*.15f,top+width*.15f),
        vertex(left+width*.8f,top+width*.15f),
        vertex(left+width*.15f,top+width*.8f)
    }};
    FojStage325Vertex tile[FOJ_STAGE325_TILE_VERTICES];
    FojStage325Vertex rem[FOJ_STAGE325_REMAINDER_VERTICES];
    FojStage325PartitionReport r={0};
    run_partition(&inside,px,py,tile,rem,&r);
    assert(r.tile_intersects==1u&&r.tile_vertices==3u);
    assert(r.remainder_vertices==0u&&r.remainder_uv_area==0.0);
    assert(fabs(r.input_uv_area-r.tile_uv_area)<1e-9);

    FojStage325Triangle outside={{
        vertex(.1f,.1f),vertex(.15f,.1f),vertex(.12f,.15f)
    }};
    run_partition(&outside,px,py,tile,rem,&r);
    assert(r.tile_intersects==0u&&r.tile_vertices==0u);
    assert(r.remainder_vertices==3u&&r.remainder_triangles==1u);
    assert(fabs(r.input_uv_area-r.remainder_uv_area)<1e-9);
}
static void partial_tangent_and_reverse_winding(void) {
    const unsigned px=2u,py=2u;
    const float left=(float)(px*256u-8u)/1024.0f;
    const float right=(float)(px*256u+8u)/1024.0f;
    const float top=(float)(py*256u-8u)/1024.0f;
    const float bottom=(float)(py*256u+8u)/1024.0f;
    FojStage325Triangle partial={{
        vertex(left-.01f,top-.01f),
        vertex(right+.01f,top-.01f),
        vertex(left-.01f,bottom+.01f)
    }};
    FojStage325Vertex tile[FOJ_STAGE325_TILE_VERTICES];
    FojStage325Vertex rem[FOJ_STAGE325_REMAINDER_VERTICES];
    FojStage325PartitionReport r={0};
    run_partition(&partial,px,py,tile,rem,&r);
    assert(r.tile_intersects==1u&&r.tile_vertices>0u&&r.remainder_vertices>0u);
    const double sign=signed_area2(partial.point,partial.point+1u,
                                   partial.point+2u);
    for(unsigned i=0u;i<r.tile_vertices;i+=3u)
        assert(signed_area2(tile+i,tile+i+1u,tile+i+2u)*sign>0.0);
    for(unsigned i=0u;i<r.remainder_vertices;i+=3u)
        assert(signed_area2(rem+i,rem+i+1u,rem+i+2u)*sign>0.0);

    FojStage325Triangle reverse=partial;
    const FojStage325Vertex tmp=reverse.point[1];
    reverse.point[1]=reverse.point[2];reverse.point[2]=tmp;
    FojStage325PartitionReport rr={0};
    run_partition(&reverse,px,py,tile,rem,&rr);
    assert(rr.tile_intersects==1u&&rr.tile_vertices==r.tile_vertices);
    assert(rr.remainder_vertices==r.remainder_vertices);
    const double reverse_sign=signed_area2(reverse.point,reverse.point+1u,
                                           reverse.point+2u);
    for(unsigned i=0u;i<rr.tile_vertices;i+=3u)
        assert(signed_area2(tile+i,tile+i+1u,tile+i+2u)*reverse_sign>0.0);
    for(unsigned i=0u;i<rr.remainder_vertices;i+=3u)
        assert(signed_area2(rem+i,rem+i+1u,rem+i+2u)*reverse_sign>0.0);

    const float cy=(float)py*.25f;
    FojStage325Triangle tangent={{
        vertex(left-.05f,cy-.04f),vertex(left,cy),
        vertex(left-.05f,cy+.04f)
    }};
    run_partition(&tangent,px,py,tile,rem,&r);
    assert(r.tile_intersects==0u&&r.tile_vertices==0u);
    assert(r.remainder_vertices==3u);
    assert(fabs(r.input_uv_area-r.remainder_uv_area)<1e-9);
}

static void tiny_positive_intersection_refused_atomically(void) {
    const float left=(float)(2u*256u-8u)/1024.0f;
    const float top=(float)(2u*256u-8u)/1024.0f;
    const float left_out=nextafterf(left,-INFINITY);
    const float left_in=nextafterf(left,INFINITY);
    const float top_out=nextafterf(top,-INFINITY);
    const float top_in=nextafterf(top,INFINITY);
    FojStage325Triangle tiny={{
        vertex(left_out,top_in),
        vertex(left_in,top_out),
        vertex(left_in,top_in)
    }};
    assert(fabs(signed_area2(tiny.point,tiny.point+1u,tiny.point+2u))>1e-16);
    FojStage325Vertex tile[FOJ_STAGE325_TILE_VERTICES];
    FojStage325Vertex rem[FOJ_STAGE325_REMAINDER_VERTICES];
    FojStage325Vertex saved_tile[FOJ_STAGE325_TILE_VERTICES];
    FojStage325Vertex saved_rem[FOJ_STAGE325_REMAINDER_VERTICES];
    FojStage325PartitionReport r,saved_r;
    memset(tile,0xa5,sizeof(tile));memset(rem,0x5a,sizeof(rem));
    memset(&r,0x3c,sizeof(r));
    memcpy(saved_tile,tile,sizeof(tile));memcpy(saved_rem,rem,sizeof(rem));
    memcpy(&saved_r,&r,sizeof(r));
    assert(!foj_stage325_partition_triangle_at_corner_tile(
        &tiny,2u,2u,tile,FOJ_STAGE325_TILE_VERTICES,
        rem,FOJ_STAGE325_REMAINDER_VERTICES,&r));
    assert(memcmp(tile,saved_tile,sizeof(tile))==0);
    assert(memcmp(rem,saved_rem,sizeof(rem))==0);
    assert(memcmp(&r,&saved_r,sizeof(r))==0);
}

static void near_duplicate_boundary_vertex_loss_refused_atomically(void) {
    const float left=(float)(2u*256u-8u)/1024.0f;
    const float right=(float)(2u*256u+8u)/1024.0f;
    const float top=(float)(2u*256u-8u)/1024.0f;
    const float bottom=(float)(2u*256u+8u)/1024.0f;
    const float left_inside=nextafterf(left,INFINITY);
    const float top_inside=nextafterf(top,INFINITY);
    const float right_inside=nextafterf(right,-INFINITY);
    const float bottom_inside=nextafterf(bottom,-INFINITY);
    FojStage325Triangle t={{
        vertex(left_inside,top_inside),
        vertex(left-0.1f,top_inside),
        vertex(right_inside,bottom_inside)
    }};
    FojStage324Vertex stage324_output[FOJ_STAGE324_MAX_OUTPUT_VERTICES];
    FojStage324TileClipReport stage324_report={0};
    assert(foj_stage324_clip_triangle_to_corner_tile(
        &t,2u,2u,stage324_output,
        FOJ_STAGE324_MAX_OUTPUT_VERTICES,&stage324_report));
    /* Stage324's epsilon dedup drops the near-left boundary point but still
     * leaves a nonempty triangle, so a boolean-only check is insufficient. */
    assert(stage324_report.intersects==1u);
    assert(stage324_report.output_vertices==3u);
    assert(stage324_report.clipped_uv_area>0.0);

    FojStage325Vertex tile[FOJ_STAGE325_TILE_VERTICES];
    FojStage325Vertex rem[FOJ_STAGE325_REMAINDER_VERTICES];
    FojStage325Vertex saved_tile[FOJ_STAGE325_TILE_VERTICES];
    FojStage325Vertex saved_rem[FOJ_STAGE325_REMAINDER_VERTICES];
    FojStage325PartitionReport r,saved_r;
    memset(tile,0xa5,sizeof(tile));memset(rem,0x5a,sizeof(rem));
    memset(&r,0x3c,sizeof(r));
    memcpy(saved_tile,tile,sizeof(tile));memcpy(saved_rem,rem,sizeof(rem));
    memcpy(&saved_r,&r,sizeof(r));
    assert(!foj_stage325_partition_triangle_at_corner_tile(
        &t,2u,2u,tile,FOJ_STAGE325_TILE_VERTICES,
        rem,FOJ_STAGE325_REMAINDER_VERTICES,&r));
    assert(memcmp(tile,saved_tile,sizeof(tile))==0);
    assert(memcmp(rem,saved_rem,sizeof(rem))==0);
    assert(memcmp(&r,&saved_r,sizeof(r))==0);
}

static uint32_t rng_state=UINT32_C(0x13579bdf);
static float next_unit(void) {
    rng_state=rng_state*UINT32_C(1664525)+UINT32_C(1013904223);
    return (float)(rng_state>>8)*(1.0f/16777216.0f);
}
static void randomized_area_conservation(void) {
    FojStage325Vertex tile[FOJ_STAGE325_TILE_VERTICES];
    FojStage325Vertex rem[FOJ_STAGE325_REMAINDER_VERTICES];
    unsigned checked=0u;
    for(unsigned i=0u;i<2048u;++i) {
        const float u0=next_unit(),v0=next_unit();
        const float u1=next_unit(),v1=next_unit();
        const float u2=next_unit(),v2=next_unit();
        FojStage325Triangle t={{
            vertex(u0,v0),vertex(u1,v1),vertex(u2,v2)
        }};
        if(fabs(signed_area2(t.point,t.point+1u,t.point+2u))<1e-7)
            continue;
        const unsigned px=1u+(i%3u);
        const unsigned py=1u+((i/3u)%3u);
        FojStage325PartitionReport r={0};
        run_partition(&t,px,py,tile,rem,&r);
        assert(r.tile_vertices<=FOJ_STAGE325_TILE_VERTICES);
        assert(r.remainder_vertices<=FOJ_STAGE325_REMAINDER_VERTICES);
        ++checked;
    }
    assert(checked>=2040u);
}

static void deterministic_and_atomic_failures(void) {
    FojStage325Triangle t=covering_triangle(2u,2u);
    FojStage325Vertex tile[FOJ_STAGE325_TILE_VERTICES],tile2[FOJ_STAGE325_TILE_VERTICES];
    FojStage325Vertex rem[FOJ_STAGE325_REMAINDER_VERTICES],rem2[FOJ_STAGE325_REMAINDER_VERTICES];
    FojStage325PartitionReport r={0},r2={0};
    run_partition(&t,2u,2u,tile,rem,&r);
    assert(foj_stage325_partition_triangle_at_corner_tile(
        &t,2u,2u,tile2,FOJ_STAGE325_TILE_VERTICES,
        rem2,FOJ_STAGE325_REMAINDER_VERTICES,&r2));
    assert(memcmp(tile,tile2,sizeof(tile))==0);
    assert(memcmp(rem,rem2,sizeof(rem))==0);
    assert(memcmp(&r,&r2,sizeof(r))==0);

    FojStage325Vertex saved_tile[FOJ_STAGE325_TILE_VERTICES];
    FojStage325Vertex saved_rem[FOJ_STAGE325_REMAINDER_VERTICES];
    FojStage325PartitionReport saved_r;
    memset(tile,0xa5,sizeof(tile));memset(rem,0x5a,sizeof(rem));
    memset(&r,0x3c,sizeof(r));
    memcpy(saved_tile,tile,sizeof(tile));memcpy(saved_rem,rem,sizeof(rem));
    memcpy(&saved_r,&r,sizeof(r));
    assert(!foj_stage325_partition_triangle_at_corner_tile(
        &t,0u,2u,tile,FOJ_STAGE325_TILE_VERTICES,
        rem,FOJ_STAGE325_REMAINDER_VERTICES,&r));
    assert(memcmp(tile,saved_tile,sizeof(tile))==0);
    assert(memcmp(rem,saved_rem,sizeof(rem))==0&&memcmp(&r,&saved_r,sizeof(r))==0);
    assert(!foj_stage325_partition_triangle_at_corner_tile(
        &t,2u,2u,tile,FOJ_STAGE325_TILE_VERTICES-1u,
        rem,FOJ_STAGE325_REMAINDER_VERTICES,&r));
    assert(memcmp(tile,saved_tile,sizeof(tile))==0);
    assert(memcmp(rem,saved_rem,sizeof(rem))==0&&memcmp(&r,&saved_r,sizeof(r))==0);
    assert(!foj_stage325_partition_triangle_at_corner_tile(
        &t,2u,2u,tile,FOJ_STAGE325_TILE_VERTICES,
        rem,FOJ_STAGE325_REMAINDER_VERTICES-1u,&r));
    assert(memcmp(tile,saved_tile,sizeof(tile))==0);
    assert(memcmp(rem,saved_rem,sizeof(rem))==0&&memcmp(&r,&saved_r,sizeof(r))==0);
    t.point[0].u=NAN;
    assert(!foj_stage325_partition_triangle_at_corner_tile(
        &t,2u,2u,tile,FOJ_STAGE325_TILE_VERTICES,
        rem,FOJ_STAGE325_REMAINDER_VERTICES,&r));
    assert(memcmp(tile,saved_tile,sizeof(tile))==0);
    assert(memcmp(rem,saved_rem,sizeof(rem))==0&&memcmp(&r,&saved_r,sizeof(r))==0);
    t=covering_triangle(2u,2u);
    assert(!foj_stage325_partition_triangle_at_corner_tile(
        &t,2u,2u,tile,FOJ_STAGE325_TILE_VERTICES,
        tile,FOJ_STAGE325_REMAINDER_VERTICES,&r));
    assert(memcmp(tile,saved_tile,sizeof(tile))==0);
    assert(memcmp(rem,saved_rem,sizeof(rem))==0&&memcmp(&r,&saved_r,sizeof(r))==0);
    assert(!foj_stage325_partition_triangle_at_corner_tile(
        &t,2u,2u,(FojStage325Vertex *)&t,FOJ_STAGE325_TILE_VERTICES,
        rem,FOJ_STAGE325_REMAINDER_VERTICES,&r));
    assert(memcmp(rem,saved_rem,sizeof(rem))==0&&memcmp(&r,&saved_r,sizeof(r))==0);
    assert(!foj_stage325_partition_triangle_at_corner_tile(
        &t,2u,2u,tile,FOJ_STAGE325_TILE_VERTICES,
        rem,FOJ_STAGE325_REMAINDER_VERTICES,
        (FojStage325PartitionReport *)tile));
    assert(memcmp(tile,saved_tile,sizeof(tile))==0);
}
int main(void) {
    all_nine_corners();
    wholly_inside_and_outside();
    partial_tangent_and_reverse_winding();
    tiny_positive_intersection_refused_atomically();
    near_duplicate_boundary_vertex_loss_refused_atomically();
    randomized_area_conservation();
    deterministic_and_atomic_failures();
    puts("STAGE325_CORNER_TILE_COMPLEMENTARY_PARTITION_PASS");
    return 0;
}
