#include "stage327_ordered_partition_stream.h"
#include <assert.h>
#include <math.h>
#include <stdio.h>
#include <string.h>

static FojStage325Triangle input[FOJ_STAGE327_MAX_SOURCE_TRIANGLES];
static FojTexturedVertex stream_a[FOJ_STAGE327_MAX_VERTICES];
static FojTexturedVertex stream_b[FOJ_STAGE327_MAX_VERTICES];
static FojTexturedVertex saved_stream[FOJ_STAGE327_MAX_VERTICES];
static FojTextureSection sections_a[FOJ_STAGE327_MAX_SECTIONS];
static FojTextureSection sections_b[FOJ_STAGE327_MAX_SECTIONS];
static FojTextureSection saved_sections[FOJ_STAGE327_MAX_SECTIONS];
static FojGpuVertex gpu_vertices[FOJ_STAGE327_MAX_VERTICES];
static FojGpuBatch gpu_batches[FOJ_STAGE327_MAX_SECTIONS];
static union {
    FojTexturedVertex vertices[FOJ_STAGE327_MAX_VERTICES];
    FojTextureSection sections[FOJ_STAGE327_MAX_SECTIONS];
} alias_buffer;

static FojStage325Vertex vertex(float u,float v,float z) {
    FojStage325Vertex p={2.0f*u+v,-u+3.0f*v,z,u,v};
    return p;
}
static FojStage325Triangle make_triangle(float u0,float v0,float u1,float v1,
                                         float u2,float v2,float z) {
    FojStage325Triangle t={{
        vertex(u0,v0,z),vertex(u1,v1,z+.1f),vertex(u2,v2,z+.2f)
    }};
    return t;
}
static int same_vertex(const FojTexturedVertex *a,const FojStage325Vertex *b) {
    return a->x==b->x&&a->y==b->y&&a->z==b->z&&a->u==b->u&&a->v==b->v;
}
static void test_ordered_stream_and_gpu_projection(void) {
    input[0]=make_triangle(.45f,.45f,.55f,.45f,.50f,.56f,.2f);
    input[1]=make_triangle(.10f,.10f,.20f,.10f,.10f,.20f,.5f);
    input[2]=make_triangle(.496f,.496f,.504f,.496f,.500f,.504f,.8f);
    memset(stream_a,0xa5,sizeof(stream_a));
    memset(sections_a,0x5a,sizeof(sections_a));
    FojStage327StreamReport report;
    memset(&report,0x3c,sizeof(report));
    assert(foj_stage327_build_ordered_partition_stream(
        input,3u,2u,2u,0u,1u,2u,
        stream_a,FOJ_STAGE327_MAX_VERTICES,
        sections_a,FOJ_STAGE327_MAX_SECTIONS,&report));

    assert(report.source_triangles==3u);
    assert(report.output_vertices>0u&&report.output_vertices<=3u*57u);
    assert(report.output_sections==4u);
    assert(report.tile_fragments==2u&&report.remainder_fragments==2u);
    assert(report.tile_triangles>0u&&report.remainder_triangles>0u);

    assert(sections_a[0].first_vertex==0u);
    assert(sections_a[0].texture_index==0u);
    assert(sections_a[1].first_vertex==sections_a[0].vertex_count);
    assert(sections_a[1].texture_index==1u);
    assert(sections_a[2].first_vertex==
           sections_a[1].first_vertex+sections_a[1].vertex_count);
    assert(sections_a[2].texture_index==0u);
    assert(sections_a[2].vertex_count==3u);
    assert(sections_a[3].first_vertex==
           sections_a[2].first_vertex+sections_a[2].vertex_count);
    assert(sections_a[3].texture_index==1u);
    assert(sections_a[3].first_vertex+sections_a[3].vertex_count==
           report.output_vertices);

    FojStage325Vertex tile[FOJ_STAGE325_TILE_VERTICES]={{0}};
    FojStage325Vertex remainder[FOJ_STAGE325_REMAINDER_VERTICES]={{0}};
    FojStage325PartitionReport direct={0};
    assert(foj_stage325_partition_triangle_at_corner_tile(
        input,2u,2u,tile,FOJ_STAGE325_TILE_VERTICES,
        remainder,FOJ_STAGE325_REMAINDER_VERTICES,&direct));
    assert(sections_a[0].vertex_count==direct.remainder_vertices);
    assert(sections_a[1].vertex_count==direct.tile_vertices);
    for(unsigned i=0u;i<direct.remainder_vertices;++i)
        assert(same_vertex(stream_a+i,remainder+i));
    for(unsigned i=0u;i<direct.tile_vertices;++i)
        assert(same_vertex(stream_a+direct.remainder_vertices+i,tile+i));
    for(unsigned i=0u;i<direct.tile_vertices;++i) {
        const FojTexturedVertex *v=stream_a+direct.remainder_vertices+i;
        assert(v->u>=0.0f&&v->u<=1.0f&&v->v>=0.0f&&v->v<=1.0f);
    }

    FojTextureCamera camera={0,0,0,2,0,0,1,0};
    FojGpuStreamInfo gpu_info={0};
    assert(foj_gpu_prepare_stream(
        stream_a,report.output_vertices,sections_a,report.output_sections,2u,
        &camera,1280u,720u,gpu_vertices,FOJ_STAGE327_MAX_VERTICES,
        gpu_batches,FOJ_STAGE327_MAX_SECTIONS,&gpu_info)==FOJ_GPU_STREAM_OK);
    assert(gpu_info.vertices_written==report.output_vertices);
    assert(gpu_info.batches_written==report.output_sections);
    assert(gpu_batches[0].texture_index==0u);
    assert(gpu_batches[1].texture_index==1u);
    assert(gpu_batches[2].texture_index==0u);
    assert(gpu_batches[3].texture_index==1u);
    assert(gpu_info.camera_depth_max>gpu_info.camera_depth_min);

    FojStage327StreamReport report_b={0};
    assert(foj_stage327_build_ordered_partition_stream(
        input,3u,2u,2u,0u,1u,2u,
        stream_b,FOJ_STAGE327_MAX_VERTICES,
        sections_b,FOJ_STAGE327_MAX_SECTIONS,&report_b));
    assert(memcmp(stream_a,stream_b,sizeof(stream_a))==0);
    assert(memcmp(sections_a,sections_b,sizeof(sections_a))==0);
    assert(memcmp(&report,&report_b,sizeof(report))==0);
}
static void test_fail_closed_preflight(void) {
    input[0]=make_triangle(.45f,.45f,.55f,.45f,.50f,.56f,.2f);
    input[1]=make_triangle(.10f,.10f,.20f,.10f,.10f,.20f,.5f);
    input[2]=make_triangle(.496f,.496f,.504f,.496f,.500f,.504f,.8f);
    memset(stream_a,0xa5,sizeof(stream_a));
    memset(sections_a,0x5a,sizeof(sections_a));
    FojStage327StreamReport report;
    memset(&report,0x3c,sizeof(report));
    memcpy(saved_stream,stream_a,sizeof(stream_a));
    memcpy(saved_sections,sections_a,sizeof(sections_a));
    FojStage327StreamReport saved_report;
    memcpy(&saved_report,&report,sizeof(report));

    assert(!foj_stage327_build_ordered_partition_stream(
        input,3u,2u,2u,0u,1u,2u,
        stream_a,3u*57u-1u,sections_a,FOJ_STAGE327_MAX_SECTIONS,&report));
    assert(memcmp(stream_a,saved_stream,sizeof(stream_a))==0);
    assert(memcmp(sections_a,saved_sections,sizeof(sections_a))==0);
    assert(memcmp(&report,&saved_report,sizeof(report))==0);

    assert(!foj_stage327_build_ordered_partition_stream(
        input,3u,2u,2u,0u,0u,2u,
        stream_a,FOJ_STAGE327_MAX_VERTICES,
        sections_a,FOJ_STAGE327_MAX_SECTIONS,&report));
    assert(memcmp(stream_a,saved_stream,sizeof(stream_a))==0);
    assert(memcmp(sections_a,saved_sections,sizeof(sections_a))==0);
    assert(memcmp(&report,&saved_report,sizeof(report))==0);

    input[2].point[1].u=NAN;
    assert(!foj_stage327_build_ordered_partition_stream(
        input,3u,2u,2u,0u,1u,2u,
        stream_a,FOJ_STAGE327_MAX_VERTICES,
        sections_a,FOJ_STAGE327_MAX_SECTIONS,&report));
    assert(memcmp(stream_a,saved_stream,sizeof(stream_a))==0);
    assert(memcmp(sections_a,saved_sections,sizeof(sections_a))==0);
    assert(memcmp(&report,&saved_report,sizeof(report))==0);

    input[2].point[1].u=.504f;
    memset(alias_buffer.vertices,0xa5,sizeof(alias_buffer.vertices));
    memcpy(saved_stream,alias_buffer.vertices,sizeof(saved_stream));
    assert(!foj_stage327_build_ordered_partition_stream(
        input,3u,2u,2u,0u,1u,2u,
        alias_buffer.vertices,FOJ_STAGE327_MAX_VERTICES,
        alias_buffer.sections,FOJ_STAGE327_MAX_SECTIONS,&report));
    assert(memcmp(alias_buffer.vertices,saved_stream,sizeof(saved_stream))==0);
    assert(memcmp(&report,&saved_report,sizeof(report))==0);
}
int main(void) {
    test_ordered_stream_and_gpu_projection();
    test_fail_closed_preflight();
    puts("STAGE327_ORDERED_PARTITION_STREAM_PASS");
    return 0;
}
