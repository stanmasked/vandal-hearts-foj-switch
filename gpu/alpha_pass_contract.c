#include "alpha_pass_contract.h"
#include <string.h>
#include <stdio.h>

FojGpuAlphaPassStatus foj_gpu_alpha_pass_contract(
    const FojGpuDrawRange *ranges,size_t range_count,
    const uint32_t *draw_order,size_t order_count,
    FojGpuAlphaPass *out,size_t out_capacity) {
    if (!ranges || !draw_order || !out ||
        range_count!=FOJ_GPU_ALPHA_PASS_COUNT ||
        order_count!=FOJ_GPU_ALPHA_PASS_COUNT ||
        out_capacity<FOJ_GPU_ALPHA_PASS_COUNT)
        return FOJ_GPU_ALPHA_PASS_INVALID;

    /* The isolated Stage273/274 NRO only supports the exact generated
     * three-material triangle soup, no aliases or material indirection. */
    for(unsigned i=0;i<FOJ_GPU_ALPHA_PASS_COUNT;++i){
        if(ranges[i].first_vertex!=i*3u ||
           ranges[i].vertex_count!=3u ||
           ranges[i].material_index!=i)
            return FOJ_GPU_ALPHA_PASS_INVALID;
    }
    unsigned used=0;
    FojGpuAlphaPass checked[FOJ_GPU_ALPHA_PASS_COUNT]={0};
    for(unsigned pass=0;pass<FOJ_GPU_ALPHA_PASS_COUNT;++pass){
        const uint32_t index=draw_order[pass];
        if(index>=FOJ_GPU_ALPHA_PASS_COUNT || (used&(1u<<index)))
            return FOJ_GPU_ALPHA_PASS_INVALID;
        used|=1u<<index;
        const FojGpuDrawRange *range=&ranges[index];
        /* The only depth-writing opaque rear must submit before *both*
         * transparent materials. Otherwise reject before any GPU draw. */
        if(pass==0u && index!=2u)
            return FOJ_GPU_ALPHA_PASS_UNSAFE;
        if(pass!=0u && index==2u)
            return FOJ_GPU_ALPHA_PASS_UNSAFE;
        const uint32_t translucent=index!=2u;
        checked[pass]=(FojGpuAlphaPass){
            range->first_vertex,range->vertex_count,range->material_index,
            translucent,1u,!translucent
        };
    }
    if(used!=0x7u)
        return FOJ_GPU_ALPHA_PASS_INVALID;
    memcpy(out,checked,sizeof(checked));
    return FOJ_GPU_ALPHA_PASS_OK;
}

/* A small transactional diagnostic, not a GPU proof by itself. Validate
 * all descriptor flags and ranges once more before reporting them as
 * guest-native evidence. Only the two generated three-layer orders are
 * supported. The caller output must stay untouched on failure. */
int foj_gpu_alpha_pass_format_receipt(
    const FojGpuAlphaPass *passes,size_t count,
    char *out,size_t capacity) {
    if(!passes || !out || count!=FOJ_GPU_ALPHA_PASS_COUNT)
        return 0;
    unsigned used=0;
    for(unsigned i=0;i<FOJ_GPU_ALPHA_PASS_COUNT;++i) {
        const FojGpuAlphaPass *p=&passes[i];
        if(p->material_index>=3u ||
           used&(1u<<p->material_index) ||
           p->first_vertex!=p->material_index*3u ||
           p->vertex_count!=3u ||
           p->blend_enabled!=(i!=0u) ||
           p->depth_test_enabled!=1u ||
           p->depth_write_enabled==(i!=0u) ||
           (i==0u && p->material_index!=2u) ||
           (i!=0u && p->material_index==2u))
            return 0;
        used|=1u<<p->material_index;
    }
    if(used!=7u)return 0;
    char scratch[128];
    const int length=snprintf(scratch,sizeof(scratch),
        "FOJ_NATIVE_ALPHA_PASS_V1 %u:%u:%u:%u %u:%u:%u:%u %u:%u:%u:%u\n",
        passes[0].material_index,passes[0].blend_enabled,
        passes[0].depth_test_enabled,passes[0].depth_write_enabled,
        passes[1].material_index,passes[1].blend_enabled,
        passes[1].depth_test_enabled,passes[1].depth_write_enabled,
        passes[2].material_index,passes[2].blend_enabled,
        passes[2].depth_test_enabled,passes[2].depth_write_enabled);
    if(length<=0 || (size_t)length>=sizeof(scratch) ||
       (size_t)length+1u>capacity)return 0;
    memcpy(out,scratch,(size_t)length+1u);
    return 1;
}
