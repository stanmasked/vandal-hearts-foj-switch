#include "stage322_bounded_corner_tile.h"
#include <stdint.h>
#include <string.h>

static int overlap(const void *ap,size_t an,const void *bp,size_t bn) {
    const uintptr_t a=(uintptr_t)ap,b=(uintptr_t)bp;
    if(an>UINTPTR_MAX-a || bn>UINTPTR_MAX-b)return 1;
    return a<b+bn && b<a+an;
}
static uint64_t fnv1a(const uint8_t *p,size_t n) {
    uint64_t h=UINT64_C(14695981039346656037);
    for(size_t i=0;i<n;++i) {
        h^=p[i];
        h*=UINT64_C(1099511628211);
    }
    return h;
}
int foj_stage322_build_bounded_corner_tile(
    const FojStage321Command *cmd,
    unsigned px,unsigned py,
    const uint8_t *const pages[4],const size_t lengths[4],
    uint8_t *out,size_t out_len,FojStage322TileReceipt *receipt) {
    if(!cmd || !pages || !lengths || !out || !receipt ||
       px==0u || py==0u || px>=FOJ_BC1_PAGES_PER_SIDE ||
       py>=FOJ_BC1_PAGES_PER_SIDE ||
       out_len!=FOJ_STAGE322_TILE_BYTES ||
       overlap(cmd,sizeof(*cmd),out,out_len) ||
       overlap(cmd,sizeof(*cmd),receipt,sizeof(*receipt)) ||
       overlap(out,out_len,receipt,sizeof(*receipt)) ||
       overlap(out,out_len,pages,4u*sizeof(*pages)) ||
       overlap(out,out_len,lengths,4u*sizeof(*lengths)) ||
       overlap(receipt,sizeof(*receipt),pages,4u*sizeof(*pages)) ||
       overlap(receipt,sizeof(*receipt),lengths,4u*sizeof(*lengths)))
        return 0;

    const unsigned nw=(py-1u)*FOJ_BC1_PAGES_PER_SIDE+(px-1u);
    const uint8_t page_id[4]={
        (uint8_t)nw,(uint8_t)(nw+1u),
        (uint8_t)(nw+FOJ_BC1_PAGES_PER_SIDE),
        (uint8_t)(nw+FOJ_BC1_PAGES_PER_SIDE+1u)
    };
    uint16_t mask=0u;
    for(unsigned i=0;i<4u;++i)mask|=(uint16_t)(1u<<page_id[i]);
    if(cmd->kind!=FOJ_STAGE321_PATCH_REQUIRED || cmd->reserved ||
       cmd->filter_mask!=mask || !cmd->geometry_mask ||
       (cmd->filter_mask&cmd->geometry_mask)!=cmd->geometry_mask ||
       cmd->halo_mask!=(uint16_t)(mask&~cmd->geometry_mask) ||
       cmd->bound_count || cmd->uploaded_count)
        return 0;
    for(unsigned i=0;i<FOJ_STAGE321_TEXTURE_SLOTS;++i) {
        if(cmd->uploaded_page[i]!=FOJ_STAGE321_EMPTY_PAGE ||
           cmd->bound_slot[i]!=FOJ_STAGE321_EMPTY_PAGE)
            return 0;
        const unsigned resident=cmd->resident_page[i];
        if(resident!=FOJ_STAGE321_EMPTY_PAGE &&
           resident>=FOJ_BC1_PAGE_COUNT)return 0;
        if(resident==FOJ_STAGE321_EMPTY_PAGE)continue;
        for(unsigned j=0;j<i;++j)
            if(resident==cmd->resident_page[j])return 0;
    }
    for(unsigned i=0;i<4u;++i) {
        if(!pages[i] || lengths[i]!=FOJ_BC1_PAGE_RGBA_BYTES ||
           overlap(pages[i],lengths[i],out,out_len) ||
           overlap(pages[i],lengths[i],receipt,sizeof(*receipt)) ||
           overlap(pages[i],lengths[i],cmd,sizeof(*cmd)))
            return 0;
        for(unsigned j=0;j<i;++j)
            if(overlap(pages[i],lengths[i],pages[j],lengths[j]))
                return 0;
    }

    uint8_t tile[FOJ_STAGE322_TILE_BYTES];
    for(unsigned y=0;y<FOJ_STAGE322_TILE_EDGE;++y) {
        for(unsigned x=0;x<FOJ_STAGE322_TILE_EDGE;++x) {
            const unsigned corner=(y>=8u?2u:0u)+(x>=8u?1u:0u);
            const unsigned sx=x<8u?248u+x:x-8u;
            const unsigned sy=y<8u?248u+y:y-8u;
            const size_t si=((size_t)sy*FOJ_BC1_PAGE_EDGE+sx)*4u;
            const size_t di=((size_t)y*FOJ_STAGE322_TILE_EDGE+x)*4u;
            memcpy(tile+di,pages[corner]+si,4u);
        }
    }
    FojStage322TileReceipt value={0};
    value.atlas_first_x=px*FOJ_BC1_PAGE_EDGE-8u;
    value.atlas_first_y=py*FOJ_BC1_PAGE_EDGE-8u;
    value.source_page_mask=mask;
    memcpy(value.page_id,page_id,4u);
    for(unsigned channel=0;channel<4u;++channel) {
        const unsigned a=tile[((7u*16u+7u)*4u)+channel];
        const unsigned b=tile[((7u*16u+8u)*4u)+channel];
        const unsigned c=tile[((8u*16u+7u)*4u)+channel];
        const unsigned d=tile[((8u*16u+8u)*4u)+channel];
        value.midpoint_rgba[channel]=(uint8_t)((a+b+c+d+2u)/4u);
    }
    value.bytes_written=FOJ_STAGE322_TILE_BYTES;
    value.fnv1a64=fnv1a(tile,sizeof(tile));
    /* Sole commit after complete preflight and tile construction. */
    memcpy(out,tile,sizeof(tile));
    *receipt=value;
    return 1;
}
