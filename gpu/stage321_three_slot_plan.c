#include "stage321_three_slot_plan.h"
#include <stdint.h>
#include <string.h>

static int spans_overlap(const void *ap,size_t an,const void *bp,size_t bn) {
    const uintptr_t a=(uintptr_t)ap,b=(uintptr_t)bp;
    if(an>UINTPTR_MAX-a || bn>UINTPTR_MAX-b)return 1;
    return a<b+bn && b<a+an;
}
static unsigned count_bits(uint16_t mask) {
    unsigned n=0;
    for(unsigned i=0;i<16u;++i)n+=(mask>>i)&1u;
    return n;
}
static unsigned slot_containing(const uint8_t slots[FOJ_STAGE321_TEXTURE_SLOTS],
                                unsigned page) {
    for(unsigned s=0u;s<FOJ_STAGE321_TEXTURE_SLOTS;++s)
        if(slots[s]==page)return s;
    return FOJ_STAGE321_TEXTURE_SLOTS;
}
static int before(const FojStage320Batch *a,const FojStage320Batch *b) {
    if(a->filter_mask!=b->filter_mask)return a->filter_mask<b->filter_mask;
    return a->geometry_mask<b->geometry_mask;
}
int foj_stage321_plan_three_slots(
    const FojStage320Batch *batches,size_t count,
    FojStage321Command *commands,size_t capacity,
    FojStage321Report *report) {
    if(!batches || !commands || !report ||
       count==0u || count>FOJ_STAGE320_MAX_TRIANGLES ||
       capacity<count || capacity>SIZE_MAX/sizeof(*commands) ||
       count>SIZE_MAX/sizeof(*batches))return 0;
    const size_t input_bytes=count*sizeof(*batches);
    const size_t output_bytes=count*sizeof(*commands);
    if(spans_overlap(batches,input_bytes,commands,output_bytes) ||
       spans_overlap(batches,input_bytes,report,sizeof(*report)) ||
       spans_overlap(commands,output_bytes,report,sizeof(*report)))
        return 0;

    /* Reject malformed descriptions before computing or writing any output.
     * Verify batches contain contiguous non-empty index ranges and strictly
     * increasing canonical (filter, geometry) keys from Stage320. */
    unsigned next_index=0u;
    for(size_t i=0u;i<count;++i) {
        const FojStage320Batch *b=batches+i;
        if(b->reserved || !b->index_count || !b->geometry_mask ||
           (b->filter_mask&b->geometry_mask)!=b->geometry_mask ||
           b->halo_mask!=(uint16_t)(b->filter_mask&~b->geometry_mask) ||
           b->first_index!=next_index ||
           b->index_count>FOJ_STAGE320_MAX_TRIANGLES-next_index ||
           (i && !before(batches+i-1u,b)))
            return 0;
        next_index+=b->index_count;
    }
    FojStage321Command staged[FOJ_STAGE320_MAX_TRIANGLES];
    FojStage321Report result={0};
    uint8_t residents[FOJ_STAGE321_TEXTURE_SLOTS];
    for(unsigned s=0;s<FOJ_STAGE321_TEXTURE_SLOTS;++s)
        residents[s]=FOJ_STAGE321_EMPTY_PAGE;
    for(unsigned i=0u;i<(unsigned)count;++i) {
        const FojStage320Batch *b=batches+i;
        FojStage321Command cmd={0};
        cmd.batch_index=i;
        cmd.geometry_mask=b->geometry_mask;
        cmd.filter_mask=b->filter_mask;
        cmd.halo_mask=b->halo_mask;
        for(unsigned s=0u;s<FOJ_STAGE321_TEXTURE_SLOTS;++s) {
            cmd.uploaded_page[s]=FOJ_STAGE321_EMPTY_PAGE;
            cmd.bound_slot[s]=FOJ_STAGE321_EMPTY_PAGE;
        }
        if(count_bits(b->filter_mask)>FOJ_STAGE321_TEXTURE_SLOTS) {
            cmd.kind=FOJ_STAGE321_PATCH_REQUIRED;
            result.patch_required_batches++;
            result.all_patch_required_pages|=b->filter_mask;
        } else {
            cmd.kind=FOJ_STAGE321_DIRECT;
            result.direct_batches++;
            result.all_direct_pages|=b->filter_mask;
            /* Necessary page set in ascending page order. Retain any
             * matching resident page. First use the lowest EMPTY slot;
             * if full, evict the highest slot not needed in this batch. */
            for(unsigned page=0u;page<16u;++page) {
                if(!(b->filter_mask&(1u<<page)))continue;
                unsigned slot=slot_containing(residents,page);
                if(slot==FOJ_STAGE321_TEXTURE_SLOTS) {
                    for(unsigned s=0u;s<FOJ_STAGE321_TEXTURE_SLOTS;++s) {
                        if(residents[s]==FOJ_STAGE321_EMPTY_PAGE) {
                            slot=s;
                            break;
                        }
                    }
                    if(slot==FOJ_STAGE321_TEXTURE_SLOTS) {
                        for(unsigned s=FOJ_STAGE321_TEXTURE_SLOTS;s>0u;--s) {
                            const unsigned candidate=s-1u;
                            const unsigned old=residents[candidate];
                            if(!(b->filter_mask&(1u<<old))) {
                                slot=candidate;
                                break;
                            }
                        }
                    }
                    if(slot==FOJ_STAGE321_TEXTURE_SLOTS)return 0;
                    residents[slot]=(uint8_t)page;
                    cmd.uploaded_page[slot]=(uint8_t)page;
                    cmd.uploaded_count++;
                    result.total_page_uploads++;
                } else {
                    result.total_cached_binds++;
                }
                cmd.bound_slot[cmd.bound_count++]=(uint8_t)slot;
            }
        }
        for(unsigned s=0u;s<FOJ_STAGE321_TEXTURE_SLOTS;++s)
            cmd.resident_page[s]=residents[s];
        staged[i]=cmd;
    }
    result.commands=(unsigned)count;
    for(unsigned s=0u;s<FOJ_STAGE321_TEXTURE_SLOTS;++s)
        result.final_resident_page[s]=residents[s];
    memcpy(commands,staged,output_bytes);
    *report=result;
    return 1;
}
