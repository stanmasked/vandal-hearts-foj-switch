/* Stage321 native tests: independently replay synthetic three-slot uploads.
 * This is NOT a real GPU draw and never touches original FoJ assets. */
#include "stage321_three_slot_plan.h"
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

enum {N=FOJ_STAGE320_MAX_TRIANGLES,S=FOJ_STAGE321_TEXTURE_SLOTS};
static unsigned pop(uint16_t bits) {
    unsigned n=0;
    for(unsigned k=0;k<16u;++k)n+=(bits>>k)&1u;
    return n;
}
static FojStage320Batch batch(unsigned i,uint16_t geometry,uint16_t filter) {
    const FojStage320Batch b={
        i,1u,geometry,filter,(uint16_t)(filter&~geometry),0u
    };
    return b;
}
static void example(FojStage320Batch out[7]) {
    out[0]=batch(0u,0x0001u,0x0001u);
    out[1]=batch(1u,0x0001u,0x0003u);
    out[2]=batch(2u,0x0001u,0x0007u);
    out[3]=batch(3u,0x0007u,0x000fu); /* cannot fit 4 source pages */
    out[4]=batch(4u,0x0008u,0x0018u);
    out[5]=batch(5u,0x0008u,0x0038u);
    out[6]=batch(6u,0x0070u,0x00f0u); /* must not issue draw */
}
static unsigned find(const uint8_t slots[S],unsigned page) {
    for(unsigned s=0;s<S;++s)if(slots[s]==page)return s;
    return S;
}
static void replay(const FojStage320Batch *b,unsigned count,
                   const FojStage321Command *cmd,
                   const FojStage321Report *report) {
    uint8_t resident[S];
    for(unsigned s=0;s<S;++s)resident[s]=FOJ_STAGE321_EMPTY_PAGE;
    unsigned direct=0u,deferred=0u,uploads=0u,reuses=0u;
    uint16_t direct_mask=0u,patch_mask=0u;
    for(unsigned i=0u;i<count;++i) {
        const FojStage321Command *c=cmd+i;
        assert(c->batch_index==i && c->reserved==0u);
        assert(c->filter_mask==b[i].filter_mask);
        assert(c->geometry_mask==b[i].geometry_mask);
        assert(c->halo_mask==b[i].halo_mask);
        const unsigned needed=pop(c->filter_mask);
        const int patch=needed>S;
        assert(c->kind==(patch?FOJ_STAGE321_PATCH_REQUIRED:
                               FOJ_STAGE321_DIRECT));
        if(patch) {
            ++deferred;
            patch_mask|=c->filter_mask;
            assert(c->bound_count==0u);
            assert(c->uploaded_count==0u);
        } else {
            ++direct;
            direct_mask|=c->filter_mask;
            assert(c->bound_count==needed);
        }
        unsigned local_uploads=0u;
        for(unsigned s=0;s<S;++s) {
            if(c->uploaded_page[s]!=FOJ_STAGE321_EMPTY_PAGE) {
                assert(!patch);
                const unsigned page=c->uploaded_page[s];
                assert(page<16u && (c->filter_mask&(1u<<page)));
                resident[s]=(uint8_t)page;
                ++local_uploads;
            }
            assert(c->resident_page[s]==resident[s]);
        }
        assert(local_uploads==c->uploaded_count);
        uploads+=local_uploads;
        if(patch) {
            for(unsigned k=0;k<S;++k)
                assert(c->bound_slot[k]==FOJ_STAGE321_EMPTY_PAGE);
        } else {
            unsigned idx=0u;
            for(unsigned page=0;page<16u;++page) {
                if(!(c->filter_mask&(1u<<page)))continue;
                assert(idx<S);
                const unsigned slot=c->bound_slot[idx++];
                assert(slot<S && resident[slot]==page);
                assert(find(resident,page)==slot);
                if(c->uploaded_page[slot]!=page)++reuses;
            }
            for(;idx<S;++idx)
                assert(c->bound_slot[idx]==FOJ_STAGE321_EMPTY_PAGE);
            /* No physical slot may hold two copies of the same atlas page. */
            for(unsigned x=0;x<S;++x)for(unsigned y=x+1u;y<S;++y)
                assert(resident[x]==FOJ_STAGE321_EMPTY_PAGE ||
                       resident[x]!=resident[y]);
        }
    }
    assert(report->commands==count);
    assert(report->direct_batches==direct);
    assert(report->patch_required_batches==deferred);
    assert(report->total_page_uploads==uploads);
    assert(report->total_cached_binds==reuses);
    assert(report->all_direct_pages==direct_mask);
    assert(report->all_patch_required_pages==patch_mask);
    assert(report->reserved==0u);
    for(unsigned s=0;s<S;++s)
        assert(report->final_resident_page[s]==resident[s]);
}
static void known_cache_and_deferred(void) {
    FojStage320Batch input[7];example(input);
    FojStage321Command cmd[7]={0};
    FojStage321Report report={0};
    assert(foj_stage321_plan_three_slots(input,7u,cmd,7u,&report));
    replay(input,7u,cmd,&report);
    assert(report.direct_batches==5u);
    assert(report.patch_required_batches==2u);
    assert(report.total_page_uploads==6u);
    assert(report.total_cached_binds==5u);
    assert(report.all_direct_pages==0x003fu);
    assert(report.all_patch_required_pages==0x00ffu);
    /* Four-page command preserves the exact preexisting slot state. */
    for(unsigned s=0u;s<S;++s)
        assert(cmd[2].resident_page[s]==cmd[3].resident_page[s]);
    for(unsigned s=0u;s<S;++s)
        assert(cmd[5].resident_page[s]==cmd[6].resident_page[s]);
    assert(cmd[3].uploaded_count==0 && cmd[3].bound_count==0);
    FojStage321Command again[7]={0};
    FojStage321Report again_report={0};
    assert(foj_stage321_plan_three_slots(
        input,7u,again,7u,&again_report));
    assert(!memcmp(cmd,again,sizeof(cmd)));
    assert(!memcmp(&report,&again_report,sizeof(report)));
}
static void maximum_128_batches(void) {
    FojStage320Batch input[N];
    for(unsigned i=0u;i<N;++i) {
        const uint16_t mask=(uint16_t)(i*2u+1u);
        input[i]=batch(i,1u,mask);
    }
    FojStage321Command cmd[N]={0};
    FojStage321Report report={0};
    assert(foj_stage321_plan_three_slots(input,N,cmd,N,&report));
    replay(input,N,cmd,&report);
    assert(report.commands==N);
    assert(report.patch_required_batches>0u);
    assert(report.direct_batches>0u);
    assert(report.all_patch_required_pages!=0u);
}
static void failure_atomicity(void) {
    FojStage320Batch input[N]={0};
    example(input);
    FojStage321Command cmd[N],old_cmd[N];
    FojStage321Report report,old_report;
    memset(cmd,0xa6,sizeof(cmd));
    memset(&report,0x5c,sizeof(report));
    memcpy(old_cmd,cmd,sizeof(cmd));
    memcpy(&old_report,&report,sizeof(report));
    assert(!foj_stage321_plan_three_slots(NULL,7u,cmd,N,&report));
    assert(!foj_stage321_plan_three_slots(input,0u,cmd,N,&report));
    assert(!foj_stage321_plan_three_slots(input,N+1u,cmd,N,&report));
    assert(!foj_stage321_plan_three_slots(input,7u,NULL,N,&report));
    assert(!foj_stage321_plan_three_slots(input,7u,cmd,N,NULL));
    assert(!foj_stage321_plan_three_slots(input,7u,cmd,6u,&report));
    assert(!foj_stage321_plan_three_slots(input,7u,cmd,(size_t)-1,&report));
    assert(!foj_stage321_plan_three_slots(input,7u,
        (FojStage321Command*)(void*)input,N,&report));
    assert(!foj_stage321_plan_three_slots(input,7u,cmd,N,
        (FojStage321Report*)(void*)input));
    assert(!foj_stage321_plan_three_slots(input,7u,cmd,N,
        (FojStage321Report*)(void*)cmd));
    FojStage320Batch invalid[7];
    memcpy(invalid,input,sizeof(invalid));
    invalid[6].filter_mask=0u;
    assert(!foj_stage321_plan_three_slots(invalid,7u,cmd,N,&report));
    memcpy(invalid,input,sizeof(invalid));
    invalid[6].halo_mask=0u;
    assert(!foj_stage321_plan_three_slots(invalid,7u,cmd,N,&report));
    memcpy(invalid,input,sizeof(invalid));
    invalid[6].geometry_mask=0u;
    assert(!foj_stage321_plan_three_slots(invalid,7u,cmd,N,&report));
    memcpy(invalid,input,sizeof(invalid));
    invalid[6].reserved=1u;
    assert(!foj_stage321_plan_three_slots(invalid,7u,cmd,N,&report));
    memcpy(invalid,input,sizeof(invalid));
    invalid[6].first_index=8u;
    assert(!foj_stage321_plan_three_slots(invalid,7u,cmd,N,&report));
    memcpy(invalid,input,sizeof(invalid));
    invalid[6].index_count=0u;
    assert(!foj_stage321_plan_three_slots(invalid,7u,cmd,N,&report));
    memcpy(invalid,input,sizeof(invalid));
    invalid[6]=invalid[5];
    invalid[6].first_index=6u;
    assert(!foj_stage321_plan_three_slots(invalid,7u,cmd,N,&report));
    memcpy(invalid,input,sizeof(invalid));
    invalid[3]=input[4];
    invalid[3].first_index=3u;  /* out of canonical sort order */
    assert(!foj_stage321_plan_three_slots(invalid,7u,cmd,N,&report));
    assert(!memcmp(old_cmd,cmd,sizeof(cmd)));
    assert(!memcmp(&old_report,&report,sizeof(report)));
}
int main(void) {
    known_cache_and_deferred();
    maximum_128_batches();
    failure_atomicity();
    puts("STAGE321_NATIVE_THREE_SLOT_CACHE_AND_PATCH_DEFER_PASS");
    return 0;
}
