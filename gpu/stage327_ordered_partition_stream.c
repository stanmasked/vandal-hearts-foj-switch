#include "stage327_ordered_partition_stream.h"
#include <stdint.h>
#include <string.h>

static int overlaps(const void *ap,size_t an,const void *bp,size_t bn) {
    const uintptr_t a=(uintptr_t)ap,b=(uintptr_t)bp;
    if(an>UINTPTR_MAX-a||bn>UINTPTR_MAX-b)return 1;
    return a<b+bn&&b<a+an;
}
static int valid_partition_report(const FojStage325PartitionReport *r) {
    return r->tile_vertices<=FOJ_STAGE325_TILE_VERTICES&&
        r->remainder_vertices<=FOJ_STAGE325_REMAINDER_VERTICES&&
        r->tile_vertices%3u==0u&&r->remainder_vertices%3u==0u&&
        r->tile_triangles==r->tile_vertices/3u&&
        r->remainder_triangles==r->remainder_vertices/3u&&
        (r->tile_vertices!=0u||r->remainder_vertices!=0u);
}
static int partition_one(const FojStage325Triangle *triangle,
                         unsigned px,unsigned py,
                         FojStage325Vertex *tile,unsigned *tile_count,
                         FojStage325Vertex *remainder,unsigned *remainder_count,
                         FojStage325PartitionReport *report) {
    memset(report,0,sizeof(*report));
    if(!foj_stage325_partition_triangle_at_corner_tile(
        triangle,px,py,tile,FOJ_STAGE325_TILE_VERTICES,
        remainder,FOJ_STAGE325_REMAINDER_VERTICES,report))return 0;
    if(!valid_partition_report(report))return 0;
    *tile_count=report->tile_vertices;
    *remainder_count=report->remainder_vertices;
    return 1;
}
static void append_vertices(FojTexturedVertex *out,size_t *written,
                            const FojStage325Vertex *in,unsigned count) {
    for(unsigned i=0u;i<count;++i) {
        out[*written]=(FojTexturedVertex){
            in[i].x,in[i].y,in[i].z,in[i].u,in[i].v
        };
        ++*written;
    }
}
static void append_section(FojTextureSection *out,size_t *written,
                           size_t first,size_t count,unsigned material) {
    FojTextureSection *section=out+*written;
    memset(section,0,sizeof(*section));
    section->first_vertex=first;
    section->vertex_count=count;
    section->texture_index=material;
    ++*written;
}

int foj_stage327_build_ordered_partition_stream(
    const FojStage325Triangle *triangles,size_t triangle_count,
    unsigned px,unsigned py,unsigned source_material,unsigned tile_material,
    size_t texture_count,FojTexturedVertex *vertices_out,size_t vertex_capacity,
    FojTextureSection *sections_out,size_t section_capacity,
    FojStage327StreamReport *report_out) {
    if(!triangles||!vertices_out||!sections_out||!report_out)return 0;
    if(triangle_count==0u||triangle_count>FOJ_STAGE327_MAX_SOURCE_TRIANGLES||
       px==0u||py==0u||px>=4u||py>=4u||
       texture_count<2u||texture_count>FOJ_GPU_MAX_TEXTURES||
       source_material>=texture_count||tile_material>=texture_count||
       source_material==tile_material)return 0;

    const size_t max_vertices=triangle_count*
        (FOJ_STAGE325_TILE_VERTICES+FOJ_STAGE325_REMAINDER_VERTICES);
    const size_t max_sections=triangle_count*2u;
    if(vertex_capacity<max_vertices||vertex_capacity>FOJ_STAGE327_MAX_VERTICES||
       section_capacity<max_sections||section_capacity>FOJ_STAGE327_MAX_SECTIONS||
       max_vertices>FOJ_GPU_MAX_VERTICES||max_sections>FOJ_GPU_MAX_BATCHES)
        return 0;

    const size_t input_bytes=triangle_count*sizeof(*triangles);
    const size_t vertex_bytes=vertex_capacity*sizeof(*vertices_out);
    const size_t section_bytes=section_capacity*sizeof(*sections_out);
    if(overlaps(triangles,input_bytes,vertices_out,vertex_bytes)||
       overlaps(triangles,input_bytes,sections_out,section_bytes)||
       overlaps(triangles,input_bytes,report_out,sizeof(*report_out))||
       overlaps(vertices_out,vertex_bytes,sections_out,section_bytes)||
       overlaps(vertices_out,vertex_bytes,report_out,sizeof(*report_out))||
       overlaps(sections_out,section_bytes,report_out,sizeof(*report_out)))
        return 0;

    size_t total_vertices=0u,total_sections=0u;
    FojStage327StreamReport result;
    memset(&result,0,sizeof(result));
    result.source_triangles=(uint32_t)triangle_count;
    for(size_t i=0u;i<triangle_count;++i) {
        FojStage325Vertex tile[FOJ_STAGE325_TILE_VERTICES]={{0}};
        FojStage325Vertex remainder[FOJ_STAGE325_REMAINDER_VERTICES]={{0}};
        unsigned tile_count=0u,remainder_count=0u;
        FojStage325PartitionReport partition;
        if(!partition_one(triangles+i,px,py,tile,&tile_count,
                          remainder,&remainder_count,&partition))return 0;
        if(remainder_count) {
            total_vertices+=remainder_count;
            ++total_sections;
            ++result.remainder_fragments;
            result.remainder_triangles+=partition.remainder_triangles;
        }
        if(tile_count) {
            total_vertices+=tile_count;
            ++total_sections;
            ++result.tile_fragments;
            result.tile_triangles+=partition.tile_triangles;
        }
    }
    if(total_vertices==0u||total_vertices>vertex_capacity||
       total_vertices>FOJ_GPU_MAX_VERTICES||total_sections==0u||
       total_sections>section_capacity||total_sections>FOJ_GPU_MAX_BATCHES)
        return 0;

    /* No invalid-input path remains after this point: the second pass repeats
     * the same deterministic partition over unchanged caller-owned inputs. */
    memset(vertices_out,0,vertex_bytes);
    memset(sections_out,0,section_bytes);
    size_t vertex_written=0u,section_written=0u;
    for(size_t i=0u;i<triangle_count;++i) {
        FojStage325Vertex tile[FOJ_STAGE325_TILE_VERTICES]={{0}};
        FojStage325Vertex remainder[FOJ_STAGE325_REMAINDER_VERTICES]={{0}};
        unsigned tile_count=0u,remainder_count=0u;
        FojStage325PartitionReport partition;
        if(!partition_one(triangles+i,px,py,tile,&tile_count,
                          remainder,&remainder_count,&partition))return 0;
        if(remainder_count) {
            const size_t first=vertex_written;
            append_vertices(vertices_out,&vertex_written,remainder,remainder_count);
            append_section(sections_out,&section_written,first,remainder_count,
                           source_material);
        }
        if(tile_count) {
            const size_t first=vertex_written;
            append_vertices(vertices_out,&vertex_written,tile,tile_count);
            append_section(sections_out,&section_written,first,tile_count,
                           tile_material);
        }
    }
    if(vertex_written!=total_vertices||section_written!=total_sections)return 0;
    result.output_vertices=(uint32_t)vertex_written;
    result.output_sections=(uint32_t)section_written;
    memcpy(report_out,&result,sizeof(result));
    return 1;
}
