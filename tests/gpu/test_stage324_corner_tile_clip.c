#include "stage324_corner_tile_clip.h"
#include <assert.h>
#include <math.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

static double area2(const FojStage324Vertex *a,
                    const FojStage324Vertex *b,
                    const FojStage324Vertex *c) {
    return ((double)b->u-a->u)*((double)c->v-a->v)-
           ((double)b->v-a->v)*((double)c->u-a->u);
}
static FojStage324Vertex make_vertex(float u,float v) {
    FojStage324Vertex p={3.0f*u-1.5f,2.0f*v-.75f,
                         .2f+.25f*u+.5f*v,u,v};
    return p;
}
static FojStage324Triangle covering_triangle(unsigned px,unsigned py) {
    const float cx=(float)px*.25f,cy=(float)py*.25f;
    FojStage324Triangle t={{
        make_vertex(cx-.1f,cy-.1f),
        make_vertex(cx+.1f,cy-.1f),
        make_vertex(cx,cy+.1f)
    }};
    return t;
}
static void check_affine(const FojStage324Vertex *p,
                         unsigned px,unsigned py) {
    const double left=((double)px*256.0-8.0)/1024.0;
    const double top=((double)py*256.0-8.0)/1024.0;
    const double width=16.0/1024.0;
    const double u=left+(double)p->u*width;
    const double v=top+(double)p->v*width;
    assert(fabs((double)p->x-(3.0*u-1.5))<2e-6);
    assert(fabs((double)p->y-(2.0*v-.75))<2e-6);
    assert(fabs((double)p->z-(.2+.25*u+.5*v))<2e-6);
    assert(p->u>=0.0f&&p->u<=1.0f&&p->v>=0.0f&&p->v<=1.0f);
}
static void all_nine_full_tiles(void) {
    for(unsigned py=1u;py<=3u;++py)for(unsigned px=1u;px<=3u;++px) {
        FojStage324Triangle t=covering_triangle(px,py);
        FojStage324Vertex out[FOJ_STAGE324_MAX_OUTPUT_VERTICES];
        FojStage324Vertex again[FOJ_STAGE324_MAX_OUTPUT_VERTICES];
        FojStage324TileClipReport r={0},r2={0};
        memset(out,0xa5,sizeof(out));memset(again,0x5a,sizeof(again));
        assert(foj_stage324_clip_triangle_to_corner_tile(
            &t,px,py,out,FOJ_STAGE324_MAX_OUTPUT_VERTICES,&r));
        assert(r.intersects==1u&&r.polygon_vertices==4u);
        assert(r.output_vertices==6u&&r.output_triangles==2u);
        assert(r.atlas_first_x==px*256u-8u);
        assert(r.atlas_first_y==py*256u-8u);
        assert(fabs(r.clipped_uv_area-(16.0/1024.0)*(16.0/1024.0))<1e-10);
        assert(r.source_uv_bounds[0]==(float)(((double)px*256.0-8.0)/1024.0));
        assert(r.source_uv_bounds[1]==(float)(((double)py*256.0-8.0)/1024.0));
        assert(r.source_uv_bounds[2]==(float)(((double)px*256.0+8.0)/1024.0));
        assert(r.source_uv_bounds[3]==(float)(((double)py*256.0+8.0)/1024.0));
        for(unsigned i=0;i<r.output_vertices;++i)check_affine(out+i,px,py);
        assert(out[0].u==0.0f&&out[0].v==0.0f);
        assert(out[1].u==1.0f&&out[1].v==0.0f);
        assert(out[2].u==1.0f&&out[2].v==1.0f);
        assert(out[3].u==0.0f&&out[3].v==0.0f);
        assert(out[4].u==1.0f&&out[4].v==1.0f);
        assert(out[5].u==0.0f&&out[5].v==1.0f);
        for(unsigned i=0;i<sizeof(r.reserved);++i)assert(r.reserved[i]==0u);
        assert(foj_stage324_clip_triangle_to_corner_tile(
            &t,px,py,again,FOJ_STAGE324_MAX_OUTPUT_VERTICES,&r2));
        assert(memcmp(out,again,sizeof(out))==0);
        assert(memcmp(&r,&r2,sizeof(r))==0);
    }
}
static void partial_and_reversed(void) {
    const unsigned px=2u,py=2u;
    const float left=(float)(px*256u-8u)/1024.0f;
    const float right=(float)(px*256u+8u)/1024.0f;
    const float top=(float)(py*256u-8u)/1024.0f;
    const float bottom=(float)(py*256u+8u)/1024.0f;
    FojStage324Triangle t={{
        make_vertex(left-.01f,top-.01f),
        make_vertex(right+.01f,top-.01f),
        make_vertex(left-.01f,bottom+.01f)
    }};
    FojStage324Vertex out[FOJ_STAGE324_MAX_OUTPUT_VERTICES];
    FojStage324TileClipReport r={0};
    assert(foj_stage324_clip_triangle_to_corner_tile(
        &t,px,py,out,FOJ_STAGE324_MAX_OUTPUT_VERTICES,&r));
    assert(r.intersects==1u&&r.output_vertices>=3u);
    assert(r.output_vertices<=FOJ_STAGE324_MAX_OUTPUT_VERTICES);
    for(unsigned i=0;i<r.output_vertices;++i)check_affine(out+i,px,py);
    for(unsigned i=0;i<r.output_vertices;i+=3u)
        assert(fabs(area2(out+i,out+i+1u,out+i+2u))>1e-12);

    FojStage324Triangle reversed=t;
    const FojStage324Vertex tmp=reversed.point[1];
    reversed.point[1]=reversed.point[2];reversed.point[2]=tmp;
    FojStage324TileClipReport rr={0};
    assert(foj_stage324_clip_triangle_to_corner_tile(
        &reversed,px,py,out,FOJ_STAGE324_MAX_OUTPUT_VERTICES,&rr));
    assert(rr.intersects==1u&&rr.output_vertices==r.output_vertices);
    assert(area2(out,out+1u,out+2u)<0.0);
}
static void tangent_is_not_a_draw(void) {
    const unsigned px=2u,py=2u;
    const float left=(float)(px*256u-8u)/1024.0f;
    const float cy=(float)py*.25f;
    FojStage324Triangle t={{
        make_vertex(left-.05f,cy-.04f),
        make_vertex(left,cy),
        make_vertex(left-.05f,cy+.04f)
    }};
    FojStage324Vertex out[FOJ_STAGE324_MAX_OUTPUT_VERTICES];
    FojStage324TileClipReport r={0};
    memset(out,0xa5,sizeof(out));
    assert(foj_stage324_clip_triangle_to_corner_tile(
        &t,px,py,out,FOJ_STAGE324_MAX_OUTPUT_VERTICES,&r));
    assert(r.intersects==0u&&r.output_vertices==0u&&r.output_triangles==0u);
    FojStage324Vertex zero[FOJ_STAGE324_MAX_OUTPUT_VERTICES]={{0}};
    assert(memcmp(out,zero,sizeof(out))==0);
}
static void invalid_is_atomic(void) {
    FojStage324Triangle t=covering_triangle(2u,2u);
    FojStage324Vertex out[FOJ_STAGE324_MAX_OUTPUT_VERTICES];
    FojStage324Vertex saved[FOJ_STAGE324_MAX_OUTPUT_VERTICES];
    FojStage324TileClipReport r,saved_r;
    memset(out,0xa5,sizeof(out));memcpy(saved,out,sizeof(out));
    memset(&r,0x5a,sizeof(r));memcpy(&saved_r,&r,sizeof(r));
    assert(!foj_stage324_clip_triangle_to_corner_tile(
        &t,0u,2u,out,FOJ_STAGE324_MAX_OUTPUT_VERTICES,&r));
    assert(memcmp(out,saved,sizeof(out))==0&&memcmp(&r,&saved_r,sizeof(r))==0);
    assert(!foj_stage324_clip_triangle_to_corner_tile(
        &t,2u,2u,out,FOJ_STAGE324_MAX_OUTPUT_VERTICES-1u,&r));
    assert(memcmp(out,saved,sizeof(out))==0&&memcmp(&r,&saved_r,sizeof(r))==0);
    t.point[0].u=NAN;
    assert(!foj_stage324_clip_triangle_to_corner_tile(
        &t,2u,2u,out,FOJ_STAGE324_MAX_OUTPUT_VERTICES,&r));
    assert(memcmp(out,saved,sizeof(out))==0&&memcmp(&r,&saved_r,sizeof(r))==0);
    t=covering_triangle(2u,2u);t.point[2].u=t.point[1].u;
    t.point[2].v=t.point[1].v;
    assert(!foj_stage324_clip_triangle_to_corner_tile(
        &t,2u,2u,out,FOJ_STAGE324_MAX_OUTPUT_VERTICES,&r));
    assert(memcmp(out,saved,sizeof(out))==0&&memcmp(&r,&saved_r,sizeof(r))==0);
    assert(!foj_stage324_clip_triangle_to_corner_tile(
        &t,2u,2u,(FojStage324Vertex *)&t,
        FOJ_STAGE324_MAX_OUTPUT_VERTICES,&r));
    assert(memcmp(&r,&saved_r,sizeof(r))==0);
    assert(!foj_stage324_clip_triangle_to_corner_tile(
        &t,2u,2u,out,FOJ_STAGE324_MAX_OUTPUT_VERTICES,
        (FojStage324TileClipReport *)out));
    assert(memcmp(out,saved,sizeof(out))==0);
}
int main(void) {
    all_nine_full_tiles();
    partial_and_reversed();
    tangent_is_not_a_draw();
    invalid_is_atomic();
    puts("STAGE324_CORNER_TILE_TRIANGLE_CLIP_PASS");
    return 0;
}
