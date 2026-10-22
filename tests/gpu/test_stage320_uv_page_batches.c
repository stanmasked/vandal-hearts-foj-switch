/* Stage320: real C batch planning on entirely invented atlas UV triangles. */
#include "stage320_uv_page_batches.h"
#include <assert.h>
#include <math.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

enum { CAP=FOJ_STAGE320_MAX_TRIANGLES };
static FojStage318Triangle tri(float u0,float v0,float u1,float v1,
                               float u2,float v2) {
    const FojStage318Triangle t={{{u0,v0},{u1,v1},{u2,v2}}};
    return t;
}
static uint16_t bit(unsigned x,unsigned y) {
    return (uint16_t)(1u<<(y*4u+x));
}
static unsigned pop(uint16_t x) {
    unsigned n=0u;
    for(unsigned i=0u;i<16u;++i)n+=(x>>i)&1u;
    return n;
}
static void examples(FojStage318Triangle t[CAP]) {
    t[0]=tri(.08f,.10f,.13f,.10f,.08f,.17f);
    t[1]=tri(.49960f,.36f,.49988f,.36f,.49960f,.42f);
    t[2]=tri(.49960f,.49960f,.49990f,.49960f,.49960f,.49990f);
    t[3]=tri(.48f,.48f,.52f,.48f,.48f,.52f);
    t[4]=tri(.52f,.36f,.57f,.36f,.52f,.42f);
    t[5]=t[2];              /* same group, non-adjacent original input */
    t[6]=t[0];
    t[7]=tri(.91f,.91f,1.f,.91f,.91f,1.f);
    t[8]=t[1];
    t[9]=t[3];
    for(unsigned k=10u;k<CAP;++k) {
        /* deterministic 4x4 interior page family, many nonconsecutive
         * members of identical render groups. */
        const unsigned x=k%4u,y=(k/4u)%4u;
        const float left=x/4.f,top=y/4.f;
        t[k]=tri(left+.06f,top+.07f,
                 left+.15f,top+.07f,left+.06f,top+.16f);
    }
}
static void known_geometry_and_source_masks(
    const FojStage318Triangle *t) {
    FojStage319FilterSupport c={0};
    assert(foj_stage319_triangle_bilinear_pages(&t[0],&c));
    assert(c.geometry_page_mask==bit(0u,0u));
    assert(c.filter_page_mask==bit(0u,0u));
    assert(foj_stage319_triangle_bilinear_pages(&t[1],&c));
    assert(c.geometry_page_mask==bit(1u,1u));
    assert(c.filter_page_mask==(uint16_t)(bit(1u,1u)|bit(2u,1u)));
    assert(foj_stage319_triangle_bilinear_pages(&t[2],&c));
    assert(c.geometry_page_mask==bit(1u,1u));
    assert(c.filter_page_mask==(uint16_t)(
        bit(1u,1u)|bit(2u,1u)|bit(1u,2u)|bit(2u,2u)));
    assert(foj_stage319_triangle_bilinear_pages(&t[3],&c));
    assert(c.geometry_page_mask==(uint16_t)(
        bit(1u,1u)|bit(2u,1u)|bit(1u,2u)));
    assert(c.filter_page_mask==(uint16_t)(
        bit(1u,1u)|bit(2u,1u)|bit(1u,2u)|bit(2u,2u)));
}
static void verify_plan(const FojStage318Triangle *t,unsigned count,
                        const uint16_t *ids,const FojStage320Batch *batches,
                        const FojStage320Plan *report) {
    assert(report->triangle_count==count);
    assert(report->batch_count>0u && report->batch_count<=count);
    assert(report->reserved==0u);
    unsigned covered[CAP]={0};
    uint16_t all_geom=0u,all_filter=0u,all_halo=0u;
    unsigned total_geom_refs=0u,total_filter_refs=0u;
    unsigned next=0u;
    for(unsigned b=0u;b<report->batch_count;++b) {
        const FojStage320Batch *item=&batches[b];
        assert(item->first_index==next);
        assert(item->index_count>0u);
        assert(item->reserved==0u);
        assert(item->halo_mask==
               (uint16_t)(item->filter_mask&~item->geometry_mask));
        assert((item->filter_mask&item->geometry_mask)==item->geometry_mask);
        if(b) {
            const FojStage320Batch *prev=&batches[b-1u];
            assert(prev->filter_mask<item->filter_mask ||
                   (prev->filter_mask==item->filter_mask &&
                    prev->geometry_mask<item->geometry_mask));
        }
        unsigned last_index=0u;
        for(unsigned k=0u;k<item->index_count;++k) {
            const unsigned id=ids[next+k];
            assert(id<count);
            assert(++covered[id]==1u);
            if(k)assert(last_index<id);
            last_index=id;
            FojStage319FilterSupport expected={0};
            assert(foj_stage319_triangle_bilinear_pages(t+id,&expected));
            assert(item->geometry_mask==expected.geometry_page_mask);
            assert(item->filter_mask==expected.filter_page_mask);
            assert(item->halo_mask==expected.halo_only_page_mask);
            all_geom|=expected.geometry_page_mask;
            all_filter|=expected.filter_page_mask;
            all_halo|=expected.halo_only_page_mask;
            total_geom_refs+=pop(expected.geometry_page_mask);
            total_filter_refs+=pop(expected.filter_page_mask);
        }
        next+=item->index_count;
    }
    assert(next==count);
    for(unsigned i=0;i<count;++i)assert(covered[i]==1u);
    assert(report->all_geometry_pages==all_geom);
    assert(report->all_filter_pages==all_filter);
    assert(report->all_halo_only_pages==all_halo);
    assert(report->geometry_page_references==total_geom_refs);
    assert(report->filter_page_references==total_filter_refs);
    assert(total_filter_refs>=total_geom_refs);
}
static void sorted_stability(void) {
    FojStage318Triangle input[CAP];examples(input);
    known_geometry_and_source_masks(input);
    FojStage318Triangle copy[CAP];memcpy(copy,input,sizeof(copy));
    for(unsigned k=0u;k<3u;++k) {
        const unsigned n=k==0u?1u:(k==1u?10u:CAP);
        uint16_t ids[CAP],again_ids[CAP];
        FojStage320Batch batches[CAP],again_batches[CAP];
        FojStage320Plan info={0},again={0};
        memset(ids,0xe3,sizeof(ids));
        memset(batches,0x53,sizeof(batches));
        assert(foj_stage320_plan_triangle_batches(
            input,n,ids,CAP,batches,CAP,&info));
        verify_plan(input,n,ids,batches,&info);
        assert(foj_stage320_plan_triangle_batches(
            input,n,again_ids,CAP,again_batches,CAP,&again));
        assert(!memcmp(ids,again_ids,n*sizeof(ids[0])));
        assert(!memcmp(batches,again_batches,
                       info.batch_count*sizeof(batches[0])));
        assert(!memcmp(&info,&again,sizeof(info)));
    }
    assert(!memcmp(input,copy,sizeof(copy)));
}
static void all_sixteen_interior_pages(void) {
    FojStage318Triangle t[CAP];examples(t);
    uint16_t ids[CAP]={0};
    FojStage320Batch batches[CAP]={{0}};
    FojStage320Plan report={0};
    assert(foj_stage320_plan_triangle_batches(
        t,CAP,ids,CAP,batches,CAP,&report));
    assert(report.all_geometry_pages==UINT16_MAX);
    assert(report.all_filter_pages==UINT16_MAX);
    /* each of the 16 interior pages has at least one matching geometry
     * group; cross-seam groups increase the total distinct plan count. */
    assert(report.batch_count>=16u);
    verify_plan(t,CAP,ids,batches,&report);
}
static void reject_without_mutation(void) {
    FojStage318Triangle input[CAP];examples(input);
    uint16_t ids[CAP];FojStage320Batch batches[CAP];
    FojStage320Plan report;
    memset(ids,0xa5,sizeof(ids));
    memset(batches,0x5a,sizeof(batches));
    memset(&report,0xdd,sizeof(report));
    uint16_t saved_ids[CAP];memcpy(saved_ids,ids,sizeof(ids));
    FojStage320Batch saved_batches[CAP];
    memcpy(saved_batches,batches,sizeof(batches));
    FojStage320Plan saved_report;memcpy(&saved_report,&report,sizeof(report));
    assert(!foj_stage320_plan_triangle_batches(
        NULL,10u,ids,CAP,batches,CAP,&report));
    assert(!foj_stage320_plan_triangle_batches(
        input,0u,ids,CAP,batches,CAP,&report));
    assert(!foj_stage320_plan_triangle_batches(
        input,CAP+1u,ids,CAP,batches,CAP,&report));
    assert(!foj_stage320_plan_triangle_batches(
        input,10u,NULL,CAP,batches,CAP,&report));
    assert(!foj_stage320_plan_triangle_batches(
        input,10u,ids,CAP,NULL,CAP,&report));
    assert(!foj_stage320_plan_triangle_batches(
        input,10u,ids,CAP,batches,CAP,NULL));
    assert(!foj_stage320_plan_triangle_batches(
        input,10u,ids,9u,batches,CAP,&report));
    assert(!foj_stage320_plan_triangle_batches(
        input,10u,ids,CAP,batches,0u,&report));
    assert(!foj_stage320_plan_triangle_batches(
        input,10u,ids,CAP,batches,1u,&report));
    assert(!foj_stage320_plan_triangle_batches(
        input,10u,(uint16_t*)(void*)input,CAP,batches,CAP,&report));
    assert(!foj_stage320_plan_triangle_batches(
        input,10u,ids,CAP,batches,CAP,
        (FojStage320Plan*)(void*)input));
    assert(!foj_stage320_plan_triangle_batches(
        input,10u,ids,CAP,(FojStage320Batch*)(void*)ids,CAP,&report));
    assert(!foj_stage320_plan_triangle_batches(
        input,10u,ids,CAP,batches,CAP,
        (FojStage320Plan*)(void*)batches));
    input[CAP-1u].point[2].u=NAN;
    assert(!foj_stage320_plan_triangle_batches(
        input,CAP,ids,CAP,batches,CAP,&report));
    input[CAP-1u].point[2].u=INFINITY;
    assert(!foj_stage320_plan_triangle_batches(
        input,CAP,ids,CAP,batches,CAP,&report));
    assert(!foj_stage320_plan_triangle_batches(
        input,10u,ids,(size_t)-1,batches,CAP,&report));
    assert(!foj_stage320_plan_triangle_batches(
        input,10u,ids,CAP,batches,(size_t)-1,&report));
    assert(!memcmp(ids,saved_ids,sizeof(ids)));
    assert(!memcmp(batches,saved_batches,sizeof(batches)));
    assert(!memcmp(&report,&saved_report,sizeof(report)));
}
int main(void) {
    sorted_stability();
    all_sixteen_interior_pages();
    reject_without_mutation();
    puts("STAGE320_NATIVE_BATCH_MASKS_STABLE_IDS_ATOMIC_REJECTION_PASS");
    return 0;
}
