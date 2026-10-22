#include "stage328_atomic_corner_patch_stream.h"
#include <stdint.h>
#include <string.h>

static int spans_overlap(const void *ap,size_t an,const void *bp,size_t bn) {
    const uintptr_t a=(uintptr_t)ap,b=(uintptr_t)bp;
    if(an>UINTPTR_MAX-a||bn>UINTPTR_MAX-b)return 1;
    return a<b+bn&&b<a+an;
}
static uint16_t corner_page_mask(unsigned px,unsigned py) {
    const unsigned nw=(py-1u)*FOJ_BC1_PAGES_PER_SIDE+(px-1u);
    return (uint16_t)((1u<<nw)|(1u<<(nw+1u))|
                      (1u<<(nw+FOJ_BC1_PAGES_PER_SIDE))|
                      (1u<<(nw+FOJ_BC1_PAGES_PER_SIDE+1u)));
}
static int validate_batch_triangles(
    const FojStage320Batch *batch,
    const FojStage325Triangle *triangles,size_t count) {
    if(batch->reserved||batch->index_count!=count||
       !batch->geometry_mask||
       (batch->filter_mask&batch->geometry_mask)!=batch->geometry_mask||
       batch->halo_mask!=(uint16_t)(batch->filter_mask&~batch->geometry_mask))
        return 0;
    for(size_t i=0u;i<count;++i) {
        FojStage318Triangle uv={0};
        for(unsigned k=0u;k<3u;++k) {
            uv.point[k].u=triangles[i].point[k].u;
            uv.point[k].v=triangles[i].point[k].v;
        }
        FojStage319FilterSupport support={0};
        if(!foj_stage319_triangle_bilinear_pages(&uv,&support)||
           support.geometry_page_mask!=batch->geometry_mask||
           support.filter_page_mask!=batch->filter_mask||
           support.halo_only_page_mask!=batch->halo_mask)
            return 0;
    }
    return 1;
}
static void fill_receipt(FojStage328Receipt *out,
                         const FojStage322TileReceipt *tile,
                         const FojStage327StreamReport *stream,
                         unsigned source_texture,unsigned tile_texture) {
    memset(out,0,sizeof(*out));
    out->atlas_first_x=tile->atlas_first_x;
    out->atlas_first_y=tile->atlas_first_y;
    out->source_page_mask=tile->source_page_mask;
    memcpy(out->page_id,tile->page_id,sizeof(out->page_id));
    memcpy(out->midpoint_rgba,tile->midpoint_rgba,sizeof(out->midpoint_rgba));
    out->tile_bytes_written=tile->bytes_written;
    out->tile_fnv1a64=tile->fnv1a64;
    out->source_triangles=stream->source_triangles;
    out->output_vertices=stream->output_vertices;
    out->output_sections=stream->output_sections;
    out->tile_fragments=stream->tile_fragments;
    out->remainder_fragments=stream->remainder_fragments;
    out->tile_triangles=stream->tile_triangles;
    out->remainder_triangles=stream->remainder_triangles;
    out->source_texture_index=source_texture;
    out->tile_texture_index=tile_texture;
}
int foj_stage328_prepare_corner_patch_stream(
    const FojStage320Batch *batch,
    const FojStage325Triangle *triangles,size_t count,
    unsigned px,unsigned py,
    const uint8_t *const pages[4],const size_t lengths[4],
    unsigned source_texture,unsigned tile_texture,size_t texture_count,
    uint8_t *tile_out,size_t tile_capacity,
    FojTexturedVertex *vertices_out,size_t vertex_capacity,
    FojTextureSection *sections_out,size_t section_capacity,
    FojStage328Receipt *receipt_out) {
    if(!batch||!triangles||!pages||!lengths||!tile_out||
       !vertices_out||!sections_out||!receipt_out)return 0;
    if(count==0u||count>FOJ_STAGE328_MAX_SOURCE_TRIANGLES||
       px==0u||py==0u||px>=FOJ_BC1_PAGES_PER_SIDE||
       py>=FOJ_BC1_PAGES_PER_SIDE||
       tile_capacity!=FOJ_STAGE322_TILE_BYTES||
       texture_count<2u||texture_count>FOJ_GPU_MAX_TEXTURES||
       source_texture>=texture_count||tile_texture>=texture_count||
       source_texture==tile_texture)return 0;

    const size_t max_vertices=count*
        (FOJ_STAGE325_TILE_VERTICES+FOJ_STAGE325_REMAINDER_VERTICES);
    const size_t max_sections=count*2u;
    if(vertex_capacity<max_vertices||
       vertex_capacity>FOJ_STAGE328_MAX_VERTICES||
       section_capacity<max_sections||
       section_capacity>FOJ_STAGE328_MAX_SECTIONS||
       max_vertices>FOJ_GPU_MAX_VERTICES||
       max_sections>FOJ_GPU_MAX_BATCHES)return 0;

    const size_t triangle_bytes=count*sizeof(*triangles);
    const size_t vertex_bytes=vertex_capacity*sizeof(*vertices_out);
    const size_t section_bytes=section_capacity*sizeof(*sections_out);
    const size_t page_array_bytes=4u*sizeof(*pages);
    const size_t length_array_bytes=4u*sizeof(*lengths);
    if(spans_overlap(batch,sizeof(*batch),triangles,triangle_bytes)||
       spans_overlap(batch,sizeof(*batch),pages,page_array_bytes)||
       spans_overlap(batch,sizeof(*batch),lengths,length_array_bytes)||
       spans_overlap(triangles,triangle_bytes,pages,page_array_bytes)||
       spans_overlap(triangles,triangle_bytes,lengths,length_array_bytes)||
       spans_overlap(pages,page_array_bytes,lengths,length_array_bytes)||
       spans_overlap(batch,sizeof(*batch),tile_out,tile_capacity)||
       spans_overlap(batch,sizeof(*batch),vertices_out,vertex_bytes)||
       spans_overlap(batch,sizeof(*batch),sections_out,section_bytes)||
       spans_overlap(batch,sizeof(*batch),receipt_out,sizeof(*receipt_out))||
       spans_overlap(triangles,triangle_bytes,tile_out,tile_capacity)||
       spans_overlap(triangles,triangle_bytes,vertices_out,vertex_bytes)||
       spans_overlap(triangles,triangle_bytes,sections_out,section_bytes)||
       spans_overlap(triangles,triangle_bytes,receipt_out,sizeof(*receipt_out))||
       spans_overlap(pages,page_array_bytes,tile_out,tile_capacity)||
       spans_overlap(pages,page_array_bytes,vertices_out,vertex_bytes)||
       spans_overlap(pages,page_array_bytes,sections_out,section_bytes)||
       spans_overlap(pages,page_array_bytes,receipt_out,sizeof(*receipt_out))||
       spans_overlap(lengths,length_array_bytes,tile_out,tile_capacity)||
       spans_overlap(lengths,length_array_bytes,vertices_out,vertex_bytes)||
       spans_overlap(lengths,length_array_bytes,sections_out,section_bytes)||
       spans_overlap(lengths,length_array_bytes,receipt_out,sizeof(*receipt_out))||
       spans_overlap(tile_out,tile_capacity,vertices_out,vertex_bytes)||
       spans_overlap(tile_out,tile_capacity,sections_out,section_bytes)||
       spans_overlap(tile_out,tile_capacity,receipt_out,sizeof(*receipt_out))||
       spans_overlap(vertices_out,vertex_bytes,sections_out,section_bytes)||
       spans_overlap(vertices_out,vertex_bytes,receipt_out,sizeof(*receipt_out))||
       spans_overlap(sections_out,section_bytes,receipt_out,sizeof(*receipt_out)))
        return 0;

    for(unsigned i=0u;i<4u;++i) {
        if(!pages[i]||lengths[i]!=FOJ_BC1_PAGE_RGBA_BYTES||
           spans_overlap(pages[i],lengths[i],pages,page_array_bytes)||
           spans_overlap(pages[i],lengths[i],lengths,length_array_bytes)||
           spans_overlap(pages[i],lengths[i],batch,sizeof(*batch))||
           spans_overlap(pages[i],lengths[i],triangles,triangle_bytes)||
           spans_overlap(pages[i],lengths[i],tile_out,tile_capacity)||
           spans_overlap(pages[i],lengths[i],vertices_out,vertex_bytes)||
           spans_overlap(pages[i],lengths[i],sections_out,section_bytes)||
           spans_overlap(pages[i],lengths[i],receipt_out,sizeof(*receipt_out)))
            return 0;
        for(unsigned j=0u;j<i;++j)
            if(spans_overlap(pages[i],lengths[i],pages[j],lengths[j]))
                return 0;
    }

    const uint16_t expected_mask=corner_page_mask(px,py);
    if(batch->filter_mask!=expected_mask||
       !validate_batch_triangles(batch,triangles,count))return 0;

    /* Stage321 is re-run on a normalized single-batch descriptor. The caller
     * may have supplied this batch from a larger sorted plan with first_index
     * nonzero; the supplied triangles are already the batch's stable subset. */
    FojStage320Batch normalized=*batch;
    normalized.first_index=0u;
    FojStage321Command command={0};
    FojStage321Report planner_report={0};
    if(!foj_stage321_plan_three_slots(
        &normalized,1u,&command,1u,&planner_report)||
       command.kind!=FOJ_STAGE321_PATCH_REQUIRED)return 0;

    uint8_t tile_stage[FOJ_STAGE322_TILE_BYTES];
    FojStage322TileReceipt tile_receipt;
    if(!foj_stage322_build_bounded_corner_tile(
        &command,px,py,pages,lengths,tile_stage,sizeof(tile_stage),
        &tile_receipt))return 0;

    FojTexturedVertex vertex_stage[FOJ_STAGE328_MAX_VERTICES];
    FojTextureSection section_stage[FOJ_STAGE328_MAX_SECTIONS];
    FojStage327StreamReport stream_report;
    if(!foj_stage327_build_ordered_partition_stream(
        triangles,count,px,py,source_texture,tile_texture,texture_count,
        vertex_stage,max_vertices,section_stage,max_sections,&stream_report))
        return 0;

    FojStage328Receipt result;
    fill_receipt(&result,&tile_receipt,&stream_report,
                 source_texture,tile_texture);
    /* All validation and staging have succeeded; commit is now infallible. */
    memcpy(tile_out,tile_stage,sizeof(tile_stage));
    memcpy(vertices_out,vertex_stage,
           (size_t)stream_report.output_vertices*sizeof(*vertices_out));
    memcpy(sections_out,section_stage,
           (size_t)stream_report.output_sections*sizeof(*sections_out));
    memcpy(receipt_out,&result,sizeof(result));
    return 1;
}
