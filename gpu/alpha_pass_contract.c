#include "alpha_pass_contract.h"
#include <string.h>

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
