/* Stage322: independently verify every source pixel in a bounded corner
 * tile, nine internal 4-way junctions, and exact Stage317 bilinear samples.
 * These synthetic 16 pages are NOT original game content. */
#include "stage322_bounded_corner_tile.h"
#include "stage317_atlas_bilinear.h"
#include <assert.h>
#include <math.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

enum {N=FOJ_BC1_PAGE_COUNT, SRC_BYTES=FOJ_BC1_PAGE_RGBA_BYTES};
static uint8_t *storage[N];
static const uint8_t *pages[N];
static size_t lengths[N];
static uint64_t baseline[N];
static uint64_t hash_bytes(const uint8_t *src,size_t count) {
    uint64_t h=UINT64_C(14695981039346656037);
    for(size_t i=0;i<count;++i) {
        h^=src[i];
        h*=UINT64_C(1099511628211);
    }
    return h;
}
static uint8_t sample_formula(unsigned page,unsigned x,unsigned y,
                              unsigned channel) {
    const unsigned page_x=page%4u,page_y=page/4u;
    if(channel==0u)return (uint8_t)(11u*page+3u*x+y+page_x);
    if(channel==1u)return (uint8_t)(17u*page+x+5u*y+page_y);
    if(channel==2u)return (uint8_t)(41u*page+((x^y)&127u));
    return (uint8_t)(100u+3u*page+((x+y)&63u));
}
static void init(void) {
    for(unsigned page=0u;page<N;++page) {
        storage[page]=(uint8_t*)malloc(SRC_BYTES);
        assert(storage[page]);
        for(unsigned y=0u;y<256u;++y)
            for(unsigned x=0u;x<256u;++x)
                for(unsigned channel=0u;channel<4u;++channel)
                    storage[page][((size_t)y*256u+x)*4u+channel]=
                        sample_formula(page,x,y,channel);
        pages[page]=storage[page];
        lengths[page]=SRC_BYTES;
        baseline[page]=hash_bytes(storage[page],SRC_BYTES);
    }
}
static uint16_t mask_for(unsigned px,unsigned py) {
    const unsigned nw=(py-1u)*4u+px-1u;
    return (uint16_t)((1u<<nw)|(1u<<(nw+1u))|
                      (1u<<(nw+4u))|(1u<<(nw+5u)));
}
static FojStage321Command real_staged_patch(unsigned px,unsigned py) {
    /* A triangle entirely inside NW still needs 4 actual source pages
     * when its edges are closer than 0.5 texel to the shared corner. */
    const float x=(float)px/4.f,y=(float)py/4.f;
    const FojStage318Triangle tri={{{x-.00040f,y-.00040f},
                                    {x-.00012f,y-.00040f},
                                    {x-.00040f,y-.00012f}}};
    uint16_t ids[1]={0};
    FojStage320Batch batch[1]={{0}};
    FojStage320Plan batch_report={0};
    assert(foj_stage320_plan_triangle_batches(
        &tri,1u,ids,1u,batch,1u,&batch_report));
    assert(batch_report.batch_count==1u && ids[0]==0u);
    assert(batch[0].filter_mask==mask_for(px,py));
    FojStage321Command cmd[1]={{0}};
    FojStage321Report gpu_report={0};
    assert(foj_stage321_plan_three_slots(
        batch,1u,cmd,1u,&gpu_report));
    assert(gpu_report.patch_required_batches==1u);
    assert(gpu_report.direct_batches==0u);
    assert(gpu_report.total_page_uploads==0u);
    assert(cmd[0].kind==FOJ_STAGE321_PATCH_REQUIRED);
    return cmd[0];
}
static void verify_bilinear_center_and_neighbors(
    unsigned px,unsigned py,const uint8_t tile[FOJ_STAGE322_TILE_BYTES],
    const FojStage322TileReceipt *receipt) {
    const unsigned bx=px*256u,by=py*256u;
    const float center_u=(float)bx/1024.f;
    const float center_v=(float)by/1024.f;
    uint8_t center[4]={0};
    FojStage317RoutingReport center_route={0};
    assert(foj_stage317_sample_atlas(pages,lengths,
                                     center_u,center_v,
                                     center,&center_route));
    assert(center_route.distinct_pages==4u);
    assert(!memcmp(center,receipt->midpoint_rgba,4u));
    /* For each 5x5 quarter-texel UV, compare independent Stage317
     * original-atlas bilinear and the linear sample of tile texels. */
    for(unsigned fy=0u;fy<=4u;++fy)
        for(unsigned fx=0u;fx<=4u;++fx) {
            const float u=((float)bx-.5f+(float)fx/4.f)/1024.f;
            const float v=((float)by-.5f+(float)fy/4.f)/1024.f;
            uint8_t original[4]={0};
            FojStage317RoutingReport routing={0};
            assert(foj_stage317_sample_atlas(
                pages,lengths,u,v,original,&routing));
            assert(routing.distinct_pages==4u ||
                   fy==4u || fx==4u);
            for(unsigned channel=0u;channel<4u;++channel) {
                const unsigned nw=tile[(7u*16u+7u)*4u+channel];
                const unsigned ne=tile[(7u*16u+8u)*4u+channel];
                const unsigned sw=tile[(8u*16u+7u)*4u+channel];
                const unsigned se=tile[(8u*16u+8u)*4u+channel];
                const unsigned weighted=
                    nw*(4u-fx)*(4u-fy)+ne*fx*(4u-fy)+
                    sw*(4u-fx)*fy+se*fx*fy;
                const unsigned expected=(weighted+8u)/16u;
                assert(original[channel]==expected);
            }
        }
}
static void all_nine_four_page_tiles(void) {
    unsigned created=0u;
    for(unsigned py=1u;py<4u;++py)
      for(unsigned px=1u;px<4u;++px) {
        const FojStage321Command cmd=real_staged_patch(px,py);
        const unsigned nw=(py-1u)*4u+(px-1u);
        const uint8_t *source[4]={
            pages[nw],pages[nw+1u],pages[nw+4u],pages[nw+5u]
        };
        const size_t source_bytes[4]={
            SRC_BYTES,SRC_BYTES,SRC_BYTES,SRC_BYTES
        };
        uint8_t tile[FOJ_STAGE322_TILE_BYTES];
        memset(tile,0xcc,sizeof(tile));
        FojStage322TileReceipt receipt={0};
        assert(foj_stage322_build_bounded_corner_tile(
            &cmd,px,py,source,source_bytes,tile,sizeof(tile),&receipt));
        assert(receipt.atlas_first_x==px*256u-8u);
        assert(receipt.atlas_first_y==py*256u-8u);
        assert(receipt.source_page_mask==mask_for(px,py));
        assert(receipt.bytes_written==FOJ_STAGE322_TILE_BYTES);
        assert(receipt.fnv1a64==hash_bytes(tile,sizeof(tile)));
        for(unsigned i=0u;i<4u;++i)
            assert(receipt.page_id[i]==nw+(i&1u)+4u*(i>>1u));
        for(unsigned y=0u;y<16u;++y)
            for(unsigned x=0u;x<16u;++x) {
                const unsigned corner=(y>=8u?2u:0u)+(x>=8u?1u:0u);
                const unsigned sx=x<8u?248u+x:x-8u;
                const unsigned sy=y<8u?248u+y:y-8u;
                for(unsigned k=0u;k<4u;++k) {
                    const uint8_t expected=sample_formula(
                        receipt.page_id[corner],sx,sy,k);
                    assert(tile[((size_t)y*16u+x)*4u+k]==expected);
                }
            }
        verify_bilinear_center_and_neighbors(px,py,tile,&receipt);
        uint8_t again[FOJ_STAGE322_TILE_BYTES]={0};
        FojStage322TileReceipt receipt2={0};
        assert(foj_stage322_build_bounded_corner_tile(
            &cmd,px,py,source,source_bytes,again,sizeof(again),&receipt2));
        assert(!memcmp(tile,again,sizeof(tile)));
        assert(receipt.fnv1a64==receipt2.fnv1a64);
        ++created;
      }
    assert(created==9u);
}
static void all_failure_modes_atomic(void) {
    FojStage321Command cmd=real_staged_patch(2u,2u);
    const uint8_t *const original_pages[4]={
        pages[5],pages[6],pages[9],pages[10]
    };
    const size_t good_lengths[4]={
        SRC_BYTES,SRC_BYTES,SRC_BYTES,SRC_BYTES
    };
    uint8_t out[FOJ_STAGE322_TILE_BYTES],saved[FOJ_STAGE322_TILE_BYTES];
    memset(out,0x6c,sizeof(out));
    memcpy(saved,out,sizeof(out));
    FojStage322TileReceipt receipt;
    memset(&receipt,0x5a,sizeof(receipt));
    FojStage322TileReceipt saved_receipt;
    memcpy(&saved_receipt,&receipt,sizeof(receipt));
#define MUST_REJECT(PX,PY,P,L,DEST,SIZE,RECEIPT) \
    assert(!foj_stage322_build_bounded_corner_tile( \
        &cmd,(PX),(PY),(P),(L),(DEST),(SIZE),(RECEIPT)))
    MUST_REJECT(0u,2u,original_pages,good_lengths,out,sizeof(out),&receipt);
    MUST_REJECT(2u,4u,original_pages,good_lengths,out,sizeof(out),&receipt);
    MUST_REJECT(1u,2u,original_pages,good_lengths,out,sizeof(out),&receipt);
    MUST_REJECT(2u,2u,original_pages,good_lengths,out,sizeof(out)-1u,&receipt);
    MUST_REJECT(2u,2u,original_pages,good_lengths,out,sizeof(out)+1u,&receipt);
    MUST_REJECT(2u,2u,NULL,good_lengths,out,sizeof(out),&receipt);
    MUST_REJECT(2u,2u,original_pages,NULL,out,sizeof(out),&receipt);
    MUST_REJECT(2u,2u,original_pages,good_lengths,NULL,sizeof(out),&receipt);
    MUST_REJECT(2u,2u,original_pages,good_lengths,out,sizeof(out),NULL);
    const size_t bad_lengths[4]={
        SRC_BYTES,SRC_BYTES,SRC_BYTES,SRC_BYTES-1u
    };
    MUST_REJECT(2u,2u,original_pages,bad_lengths,out,sizeof(out),&receipt);
    const uint8_t *const bad_pages[4]={
        pages[5],pages[6],pages[9],pages[5]
    };
    MUST_REJECT(2u,2u,bad_pages,good_lengths,out,sizeof(out),&receipt);
    const uint8_t *const null_pages[4]={
        pages[5],pages[6],NULL,pages[10]
    };
    MUST_REJECT(2u,2u,null_pages,good_lengths,out,sizeof(out),&receipt);
    /* Report and output may not alias, including an interior pointer. */
    MUST_REJECT(2u,2u,original_pages,good_lengths,out,sizeof(out),
                (FojStage322TileReceipt*)(void*)(out+32u));
    /* Source bytes may not be used as a writable destination. */
    MUST_REJECT(2u,2u,original_pages,good_lengths,
                storage[5]+128u,sizeof(out),&receipt);
    FojStage321Command bad=cmd;
    bad.kind=FOJ_STAGE321_DIRECT;
    assert(!foj_stage322_build_bounded_corner_tile(
        &bad,2u,2u,original_pages,good_lengths,out,sizeof(out),&receipt));
    bad=cmd;bad.filter_mask|=1u;
    assert(!foj_stage322_build_bounded_corner_tile(
        &bad,2u,2u,original_pages,good_lengths,out,sizeof(out),&receipt));
    bad=cmd;bad.uploaded_page[0]=5u;
    assert(!foj_stage322_build_bounded_corner_tile(
        &bad,2u,2u,original_pages,good_lengths,out,sizeof(out),&receipt));
    bad=cmd;bad.bound_slot[0]=0u;
    assert(!foj_stage322_build_bounded_corner_tile(
        &bad,2u,2u,original_pages,good_lengths,out,sizeof(out),&receipt));
    bad=cmd;bad.bound_count=1u;
    assert(!foj_stage322_build_bounded_corner_tile(
        &bad,2u,2u,original_pages,good_lengths,out,sizeof(out),&receipt));
    bad=cmd;bad.resident_page[0]=16u;
    assert(!foj_stage322_build_bounded_corner_tile(
        &bad,2u,2u,original_pages,good_lengths,out,sizeof(out),&receipt));
    bad=cmd;bad.resident_page[0]=5u;bad.resident_page[1]=5u;
    assert(!foj_stage322_build_bounded_corner_tile(
        &bad,2u,2u,original_pages,good_lengths,out,sizeof(out),&receipt));
    bad=cmd;bad.halo_mask=0u;
    assert(!foj_stage322_build_bounded_corner_tile(
        &bad,2u,2u,original_pages,good_lengths,out,sizeof(out),&receipt));
    bad=cmd;bad.reserved=1u;
    assert(!foj_stage322_build_bounded_corner_tile(
        &bad,2u,2u,original_pages,good_lengths,out,sizeof(out),&receipt));
    assert(!memcmp(out,saved,sizeof(out)));
    assert(!memcmp(&receipt,&saved_receipt,sizeof(receipt)));
#undef MUST_REJECT
}
int main(void) {
    init();
    all_nine_four_page_tiles();
    all_failure_modes_atomic();
    for(unsigned i=0u;i<N;++i) {
        assert(hash_bytes(storage[i],SRC_BYTES)==baseline[i]);
        free(storage[i]);
    }
    puts("STAGE322_NINE_BOUNDED_CORNER_TILES_AND_BILINEAR_REFERENCE_PASS");
    return 0;
}
