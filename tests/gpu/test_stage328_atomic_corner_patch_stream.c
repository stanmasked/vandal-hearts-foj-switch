#include "stage328_atomic_corner_patch_stream.h"
#include "stage320_uv_page_batches.h"
#include <assert.h>
#include <math.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

enum { PAGE_BYTES=FOJ_BC1_PAGE_RGBA_BYTES, PAGE_COUNT=FOJ_BC1_PAGE_COUNT };
static uint8_t page_data[PAGE_COUNT][PAGE_BYTES];
static const uint8_t *page_ptrs[4];
static size_t page_lengths[4];
static FojStage318Triangle uv_triangles[3];
static FojStage325Triangle source_triangles[3];
static uint16_t ordered_ids[3];
static FojStage320Batch stage320_batches[3];
static FojStage320Plan stage320_report;
static uint8_t tile_a[FOJ_STAGE322_TILE_BYTES];
static uint8_t tile_b[FOJ_STAGE322_TILE_BYTES];
static uint8_t saved_tile[FOJ_STAGE322_TILE_BYTES];
static FojTexturedVertex stream_a[FOJ_STAGE328_MAX_VERTICES];
static FojTexturedVertex stream_b[FOJ_STAGE328_MAX_VERTICES];
static FojTexturedVertex saved_stream[FOJ_STAGE328_MAX_VERTICES];
static FojTextureSection sections_a[FOJ_STAGE328_MAX_SECTIONS];
static FojTextureSection sections_b[FOJ_STAGE328_MAX_SECTIONS];
static FojTextureSection saved_sections[FOJ_STAGE328_MAX_SECTIONS];
static FojGpuVertex gpu_vertices[FOJ_STAGE328_MAX_VERTICES];
static FojGpuBatch gpu_batches[FOJ_STAGE328_MAX_SECTIONS];
static FojStage328Receipt receipt_a;
static FojStage328Receipt receipt_b;
static FojStage328Receipt saved_receipt;
static union {
    uint8_t bytes[FOJ_STAGE322_TILE_BYTES];
    FojStage328Receipt receipt;
} alias_buffer;

static uint64_t hash_bytes(const uint8_t *bytes,size_t count) {
    uint64_t hash=UINT64_C(14695981039346656037);
    for(size_t i=0u;i<count;++i) {
        hash^=bytes[i];
        hash*=UINT64_C(1099511628211);
    }
    return hash;
}
static uint8_t sample(unsigned page,unsigned x,unsigned y,unsigned channel) {
    return (uint8_t)(page*37u+x*3u+y*5u+channel*47u);
}
static void init_pages(void) {
    for(unsigned p=0u;p<PAGE_COUNT;++p)
        for(unsigned y=0u;y<256u;++y)
            for(unsigned x=0u;x<256u;++x)
                for(unsigned c=0u;c<4u;++c)
                    page_data[p][((size_t)y*256u+x)*4u+c]=sample(p,x,y,c);
}
static FojStage325Triangle make_triangle(float u0,float v0,
                                         float u1,float v1,
                                         float u2,float v2,float z) {
    FojStage325Triangle triangle={0};
    triangle.point[0]=(FojStage325Vertex){100.0f*u0+v0,
        -u0+100.0f*v0,z,u0,v0};
    triangle.point[1]=(FojStage325Vertex){100.0f*u1+v1,
        -u1+100.0f*v1,z+.1f,u1,v1};
    triangle.point[2]=(FojStage325Vertex){100.0f*u2+v2,
        -u2+100.0f*v2,z+.2f,u2,v2};
    return triangle;
}
static void make_source_batch(unsigned px,unsigned py,FojStage320Batch *batch) {
    const float cx=(float)px*.25f,cy=(float)py*.25f;
    source_triangles[0]=make_triangle(
        cx-.01f,cy-.01f,cx+.01f,cy-.01f,cx,cy+.01f,.1f);
    source_triangles[1]=make_triangle(
        cx-.01f,cy+.01f,cx+.01f,cy+.01f,cx,cy-.01f,.4f);
    source_triangles[2]=make_triangle(
        cx-.01f,cy,cx+.01f,cy-.01f,cx+.01f,cy+.01f,.7f);
    for(unsigned i=0u;i<3u;++i)
        for(unsigned k=0u;k<3u;++k)
            uv_triangles[i].point[k]=(FojStage318Uv){
                source_triangles[i].point[k].u,
                source_triangles[i].point[k].v
            };
    memset(ordered_ids,0,sizeof(ordered_ids));
    memset(stage320_batches,0,sizeof(stage320_batches));
    memset(&stage320_report,0,sizeof(stage320_report));
    assert(foj_stage320_plan_triangle_batches(
        uv_triangles,3u,ordered_ids,3u,stage320_batches,3u,&stage320_report));
    assert(stage320_report.batch_count==1u);
    assert(stage320_batches[0].index_count==3u);
    assert(ordered_ids[0]==0u&&ordered_ids[1]==1u&&ordered_ids[2]==2u);
    *batch=stage320_batches[0];
    const unsigned nw=(py-1u)*4u+(px-1u);
    page_ptrs[0]=page_data[nw];
    page_ptrs[1]=page_data[nw+1u];
    page_ptrs[2]=page_data[nw+4u];
    page_ptrs[3]=page_data[nw+5u];
    for(unsigned i=0u;i<4u;++i)page_lengths[i]=PAGE_BYTES;
}
static void assert_outputs_unchanged(void) {
    assert(memcmp(tile_a,saved_tile,sizeof(tile_a))==0);
    assert(memcmp(stream_a,saved_stream,sizeof(stream_a))==0);
    assert(memcmp(sections_a,saved_sections,sizeof(sections_a))==0);
    assert(memcmp(&receipt_a,&saved_receipt,sizeof(receipt_a))==0);
}
static void verify_tile(unsigned px,unsigned py,const FojStage328Receipt *receipt) {
    const unsigned nw=(py-1u)*4u+(px-1u);
    const uint16_t expected_mask=(uint16_t)((1u<<nw)|(1u<<(nw+1u))|
        (1u<<(nw+4u))|(1u<<(nw+5u)));
    assert(receipt->atlas_first_x==px*256u-8u);
    assert(receipt->atlas_first_y==py*256u-8u);
    assert(receipt->source_page_mask==expected_mask);
    assert(receipt->page_id[0]==nw&&receipt->page_id[1]==nw+1u);
    assert(receipt->page_id[2]==nw+4u&&receipt->page_id[3]==nw+5u);
    assert(receipt->tile_bytes_written==FOJ_STAGE322_TILE_BYTES);
    assert(receipt->tile_fnv1a64==hash_bytes(tile_a,sizeof(tile_a)));
    for(unsigned y=0u;y<16u;++y)
        for(unsigned x=0u;x<16u;++x) {
            const unsigned corner=(y>=8u?2u:0u)+(x>=8u?1u:0u);
            const unsigned sx=x<8u?248u+x:x-8u;
            const unsigned sy=y<8u?248u+y:y-8u;
            for(unsigned c=0u;c<4u;++c) {
                const uint8_t expected=page_data[receipt->page_id[corner]]
                    [((size_t)sy*256u+sx)*4u+c];
                assert(tile_a[((size_t)y*16u+x)*4u+c]==expected);
            }
        }
}
static void test_all_nine_atomic_corner_batches(void) {
    for(unsigned py=1u;py<4u;++py)for(unsigned px=1u;px<4u;++px) {
        FojStage320Batch batch={0};
        make_source_batch(px,py,&batch);
        memset(tile_a,0xcc,sizeof(tile_a));
        memset(stream_a,0xa5,sizeof(stream_a));
        memset(sections_a,0x5a,sizeof(sections_a));
        memset(&receipt_a,0x3c,sizeof(receipt_a));
        assert(foj_stage328_prepare_corner_patch_stream(
            &batch,source_triangles,3u,px,py,page_ptrs,page_lengths,
            0u,1u,2u,tile_a,sizeof(tile_a),stream_a,
            FOJ_STAGE328_MAX_VERTICES,sections_a,FOJ_STAGE328_MAX_SECTIONS,
            &receipt_a));
        assert(receipt_a.source_triangles==3u);
        assert(receipt_a.output_vertices>0u&&receipt_a.output_vertices<=171u);
        assert(receipt_a.output_sections==6u);
        assert(receipt_a.tile_fragments==3u&&receipt_a.remainder_fragments==3u);
        assert(receipt_a.tile_triangles>0u&&receipt_a.remainder_triangles>0u);
        assert(receipt_a.source_texture_index==0u&&receipt_a.tile_texture_index==1u);
        assert(batch.filter_mask==receipt_a.source_page_mask);
        verify_tile(px,py,&receipt_a);

        size_t next=0u;
        for(unsigned i=0u;i<3u;++i) {
            const FojTextureSection *remainder=sections_a+2u*i;
            const FojTextureSection *tile=sections_a+2u*i+1u;
            assert(remainder->first_vertex==next);
            assert(remainder->texture_index==0u&&remainder->vertex_count>0u);
            assert(remainder->vertex_count%3u==0u);
            next+=remainder->vertex_count;
            assert(tile->first_vertex==next);
            assert(tile->texture_index==1u&&tile->vertex_count>0u);
            assert(tile->vertex_count%3u==0u);
            for(size_t j=0u;j<tile->vertex_count;++j) {
                const FojTexturedVertex *v=stream_a+tile->first_vertex+j;
                assert(v->u>=0.0f&&v->u<=1.0f);
                assert(v->v>=0.0f&&v->v<=1.0f);
            }
            next+=tile->vertex_count;
        }
        assert(next==receipt_a.output_vertices);

        FojTextureCamera camera={50.f,50.f,0.f,100.f,0.f,0.f,1.f,0};
        FojGpuStreamInfo gpu_info={0};
        assert(foj_gpu_prepare_stream(
            stream_a,receipt_a.output_vertices,sections_a,receipt_a.output_sections,
            2u,&camera,1280u,720u,gpu_vertices,FOJ_STAGE328_MAX_VERTICES,
            gpu_batches,FOJ_STAGE328_MAX_SECTIONS,&gpu_info)==FOJ_GPU_STREAM_OK);
        assert(gpu_info.vertices_written==receipt_a.output_vertices);
        assert(gpu_info.batches_written==receipt_a.output_sections);
        assert(gpu_info.camera_depth_max>gpu_info.camera_depth_min);

        memset(tile_b,0xcc,sizeof(tile_b));
        memset(stream_b,0xa5,sizeof(stream_b));
        memset(sections_b,0x5a,sizeof(sections_b));
        memset(&receipt_b,0x3c,sizeof(receipt_b));
        assert(foj_stage328_prepare_corner_patch_stream(
            &batch,source_triangles,3u,px,py,page_ptrs,page_lengths,
            0u,1u,2u,tile_b,sizeof(tile_b),stream_b,
            FOJ_STAGE328_MAX_VERTICES,sections_b,FOJ_STAGE328_MAX_SECTIONS,
            &receipt_b));
        assert(memcmp(tile_a,tile_b,sizeof(tile_a))==0);
        assert(memcmp(stream_a,stream_b,sizeof(stream_a))==0);
        assert(memcmp(sections_a,sections_b,sizeof(sections_a))==0);
        assert(memcmp(&receipt_a,&receipt_b,sizeof(receipt_a))==0);
    }
}
static void test_transactional_rejections(void) {
    FojStage320Batch batch={0};
    make_source_batch(2u,2u,&batch);
    memset(tile_a,0x6c,sizeof(tile_a));
    memset(stream_a,0xa5,sizeof(stream_a));
    memset(sections_a,0x5a,sizeof(sections_a));
    memset(&receipt_a,0x3c,sizeof(receipt_a));
    memcpy(saved_tile,tile_a,sizeof(tile_a));
    memcpy(saved_stream,stream_a,sizeof(stream_a));
    memcpy(saved_sections,sections_a,sizeof(sections_a));
    memcpy(&saved_receipt,&receipt_a,sizeof(receipt_a));

    assert(!foj_stage328_prepare_corner_patch_stream(
        &batch,source_triangles,3u,2u,2u,page_ptrs,page_lengths,
        0u,1u,2u,tile_a,sizeof(tile_a),stream_a,170u,
        sections_a,FOJ_STAGE328_MAX_SECTIONS,&receipt_a));
    assert_outputs_unchanged();

    FojStage320Batch wrong_batch=batch;
    wrong_batch.filter_mask^=1u;
    assert(!foj_stage328_prepare_corner_patch_stream(
        &wrong_batch,source_triangles,3u,2u,2u,page_ptrs,page_lengths,
        0u,1u,2u,tile_a,sizeof(tile_a),stream_a,
        FOJ_STAGE328_MAX_VERTICES,sections_a,FOJ_STAGE328_MAX_SECTIONS,
        &receipt_a));
    assert_outputs_unchanged();

    size_t saved_length=page_lengths[3];
    page_lengths[3]=PAGE_BYTES-1u;
    assert(!foj_stage328_prepare_corner_patch_stream(
        &batch,source_triangles,3u,2u,2u,page_ptrs,page_lengths,
        0u,1u,2u,tile_a,sizeof(tile_a),stream_a,
        FOJ_STAGE328_MAX_VERTICES,sections_a,FOJ_STAGE328_MAX_SECTIONS,
        &receipt_a));
    page_lengths[3]=saved_length;
    assert_outputs_unchanged();

    float saved_x=source_triangles[0].point[0].x;
    source_triangles[0].point[0].x=NAN;
    assert(!foj_stage328_prepare_corner_patch_stream(
        &batch,source_triangles,3u,2u,2u,page_ptrs,page_lengths,
        0u,1u,2u,tile_a,sizeof(tile_a),stream_a,
        FOJ_STAGE328_MAX_VERTICES,sections_a,FOJ_STAGE328_MAX_SECTIONS,
        &receipt_a));
    source_triangles[0].point[0].x=saved_x;
    assert_outputs_unchanged();

    assert(!foj_stage328_prepare_corner_patch_stream(
        &batch,source_triangles,3u,2u,2u,page_ptrs,page_lengths,
        0u,0u,2u,tile_a,sizeof(tile_a),stream_a,
        FOJ_STAGE328_MAX_VERTICES,sections_a,FOJ_STAGE328_MAX_SECTIONS,
        &receipt_a));
    assert_outputs_unchanged();

    memset(alias_buffer.bytes,0x79,sizeof(alias_buffer.bytes));
    uint8_t alias_saved[FOJ_STAGE322_TILE_BYTES];
    memcpy(alias_saved,alias_buffer.bytes,sizeof(alias_saved));
    assert(!foj_stage328_prepare_corner_patch_stream(
        &batch,source_triangles,3u,2u,2u,page_ptrs,page_lengths,
        0u,1u,2u,alias_buffer.bytes,sizeof(alias_buffer.bytes),stream_a,
        FOJ_STAGE328_MAX_VERTICES,sections_a,FOJ_STAGE328_MAX_SECTIONS,
        &alias_buffer.receipt));
    assert(memcmp(alias_buffer.bytes,alias_saved,sizeof(alias_saved))==0);
    assert_outputs_unchanged();
}
int main(void) {
    init_pages();
    test_all_nine_atomic_corner_batches();
    test_transactional_rejections();
    puts("STAGE328_ATOMIC_CORNER_PATCH_STREAM_PASS");
    return 0;
}
