#include "stage320_uv_page_batches.h"
#include <stdint.h>
#include <string.h>

static int overlaps(const void *aa,size_t an,const void *bb,size_t bn) {
    const uintptr_t a=(uintptr_t)aa,b=(uintptr_t)bb;
    if (an>UINTPTR_MAX-a || bn>UINTPTR_MAX-b)return 1;
    return a<b+bn && b<a+an;
}
static unsigned popcount16(uint16_t value) {
    unsigned sum=0u;
    for(unsigned i=0u;i<16u;++i)sum+=(value>>i)&1u;
    return sum;
}
typedef struct {uint16_t geometry,filter;} GroupKey;
static int precedes(GroupKey a,GroupKey b) {
    if(a.filter!=b.filter)return a.filter<b.filter;
    return a.geometry<b.geometry;
}
int foj_stage320_plan_triangle_batches(
    const FojStage318Triangle *triangles,size_t count,
    uint16_t *ids,size_t ids_capacity,
    FojStage320Batch *batches,size_t batch_capacity,
    FojStage320Plan *report) {
    if(!triangles || !ids || !batches || !report ||
       count==0u || count>FOJ_STAGE320_MAX_TRIANGLES ||
       ids_capacity<count || batch_capacity==0u ||
       count>SIZE_MAX/sizeof(*triangles) ||
       ids_capacity>SIZE_MAX/sizeof(*ids) ||
       batch_capacity>SIZE_MAX/sizeof(*batches))return 0;
    const size_t input_size=count*sizeof(*triangles);
    /* Only the regions actually written are checked, so a huge declared
     * capacity cannot create a pointer wrap or excuse overlapping output. */
    const size_t ids_size=count*sizeof(*ids);
    if(overlaps(triangles,input_size,ids,ids_size) ||
       overlaps(triangles,input_size,batches,
                batch_capacity*sizeof(*batches)) ||
       overlaps(triangles,input_size,report,sizeof(*report)) ||
       overlaps(ids,ids_size,batches,batch_capacity*sizeof(*batches)) ||
       overlaps(ids,ids_size,report,sizeof(*report)) ||
       overlaps(batches,batch_capacity*sizeof(*batches),report,sizeof(*report)))
        return 0;

    GroupKey each[FOJ_STAGE320_MAX_TRIANGLES];
    GroupKey distinct[FOJ_STAGE320_MAX_TRIANGLES];
    unsigned nkeys=0u;
    FojStage320Plan proposed={0};
    proposed.triangle_count=(unsigned)count;
    for(unsigned i=0u;i<(unsigned)count;++i) {
        FojStage319FilterSupport coverage={0};
        if(!foj_stage319_triangle_bilinear_pages(triangles+i,&coverage))
            return 0;
        const GroupKey key={
            coverage.geometry_page_mask,coverage.filter_page_mask
        };
        if(!key.geometry || (key.filter&key.geometry)!=key.geometry ||
           coverage.halo_only_page_mask!=(uint16_t)(key.filter&~key.geometry))
            return 0;
        each[i]=key;
        proposed.all_geometry_pages|=key.geometry;
        proposed.all_filter_pages|=key.filter;
        proposed.all_halo_only_pages|=(uint16_t)(key.filter&~key.geometry);
        proposed.geometry_page_references+=popcount16(key.geometry);
        proposed.filter_page_references+=popcount16(key.filter);
        unsigned pos=0u;
        while(pos<nkeys && precedes(distinct[pos],key))++pos;
        if(pos<nkeys &&
           distinct[pos].geometry==key.geometry &&
           distinct[pos].filter==key.filter)continue;
        for(unsigned j=nkeys;j>pos;--j)distinct[j]=distinct[j-1u];
        distinct[pos]=key;
        ++nkeys;
    }
    if(nkeys>batch_capacity)return 0;
    /* Atomic staging: never write caller outputs before full validation. */
    uint16_t sorted_ids[FOJ_STAGE320_MAX_TRIANGLES]={0};
    FojStage320Batch sorted_batches[FOJ_STAGE320_MAX_TRIANGLES]={{0}};
    unsigned next=0u;
    for(unsigned b=0u;b<nkeys;++b) {
        const unsigned first=next;
        const GroupKey key=distinct[b];
        for(unsigned i=0u;i<(unsigned)count;++i) {
            if(each[i].geometry==key.geometry && each[i].filter==key.filter)
                sorted_ids[next++]=(uint16_t)i;
        }
        if(next==first)return 0;
        sorted_batches[b]=(FojStage320Batch){
            first,next-first,key.geometry,key.filter,
            (uint16_t)(key.filter&~key.geometry),0u
        };
    }
    if(next!=count)return 0;
    proposed.batch_count=nkeys;
    /* Counts fit in native unsigned: max 128 triangles × 16 pages. */
    memcpy(ids,sorted_ids,ids_size);
    memcpy(batches,sorted_batches,(size_t)nkeys*sizeof(*batches));
    *report=proposed;
    return 1;
}
