#include "stage339_private_dds_bridge.h"
#include "stage332_dds_source.h"
#include <stdint.h>

/* Use checked half-open memory intervals for deterministic refusal. */
static int span(const void *p,size_t n,uintptr_t *begin,uintptr_t *end) {
    if(!p || !n) return 0;
    const uintptr_t v=(uintptr_t)p;
    if(n > UINTPTR_MAX-v) return 0;
    *begin=v; *end=v+n;
    return 1;
}
static int overlap(uintptr_t a,uintptr_t b,uintptr_t c,uintptr_t d) {
    return a<d && c<b;
}
int foj_stage339_prepare_private_dds(
    const uint8_t *dds,size_t dds_len,uint8_t *rgba,size_t capacity,
    uint32_t row_alignment,uint64_t image_layout_bytes,
    uint32_t image_layout_alignment,FojStage339Prepared *out) {
    uintptr_t ds,de,rs,re,os,oe;
    if(!span(dds,dds_len,&ds,&de) ||
       !span(rgba,capacity,&rs,&re) ||
       !span(out,sizeof(*out),&os,&oe) ||
       overlap(ds,de,rs,re) ||
       overlap(ds,de,os,oe) ||
       overlap(rs,re,os,oe)) return 0;
    FojStage332DdsInfo info;
    if(!foj_stage332_dds_inspect(dds,dds_len,&info) ||
       capacity<info.rgba_bytes) return 0;
    FojStage336GpuCopyPlan plan;
    if(!foj_stage336_gpu_copy_plan(&info,info.rgba_bytes,row_alignment,
       image_layout_bytes,image_layout_alignment,&plan)) return 0;

    /*
     * All bridge-owned refusal conditions are resolved before the first
     * destination write. The input bytes must remain immutable for this call:
     * inspect and decode intentionally validate the same stable byte range.
     * Stage332's decoder guarantees that a failed decode leaves both outputs
     * unchanged. After a successful decode there is no further fallible check,
     * so the bridge cannot reject after modifying rgba.
     */
    FojStage332DdsInfo decoded;
    if(!foj_stage332_dds_decode(dds,dds_len,rgba,capacity,&decoded))
        return 0;
    (void)decoded; /* same deterministic inspector; source is immutable */
    const FojStage339Prepared result={info,plan};
    *out=result;
    return 1;
}
