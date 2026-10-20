#include "alpha_pass_contract.h"
#include <stdio.h>
#include <string.h>
#include <stdint.h>

static unsigned checks;
#define CHECK(x) do {++checks;if(!(x)) { \
    fprintf(stderr,"Stage274 C alpha pass contract failed line %d: %s\n",__LINE__,#x);return 1; \
}}while(0)

static int retained(const FojGpuAlphaPass *p){
    for(unsigned i=0;i<FOJ_GPU_ALPHA_PASS_COUNT;++i)
        if(p[i].material_index!=UINT32_C(0xA5A5A5A5))return 0;
    return 1;
}
int main(void){
    const FojGpuDrawRange ranges[3]={
        {0u,3u,0u},{3u,3u,1u},{6u,3u,2u}
    };
    FojGpuAlphaPass out[3];
    const uint32_t forward[3]={2u,1u,0u};
    const uint32_t reversed[3]={2u,0u,1u};
    memset(out,0xA5,sizeof(out));
    CHECK(foj_gpu_alpha_pass_contract(ranges,3,forward,3,out,3)==FOJ_GPU_ALPHA_PASS_OK);
    for(unsigned i=0;i<3;++i){
        CHECK(out[i].material_index==forward[i]);
        CHECK(out[i].first_vertex==forward[i]*3u);
        CHECK(out[i].vertex_count==3u);
        CHECK(out[i].depth_test_enabled==1u);
        CHECK(out[i].depth_write_enabled==(i==0u));
        CHECK(out[i].blend_enabled==(i!=0u));
    }
    CHECK(foj_gpu_alpha_pass_contract(ranges,3,reversed,3,out,3)==FOJ_GPU_ALPHA_PASS_OK);
    CHECK(out[0].material_index==2u);
    CHECK(out[1].material_index==0u);
    CHECK(out[2].material_index==1u);
    CHECK(out[0].depth_write_enabled==1u);
    CHECK(out[1].depth_write_enabled==0u);
    CHECK(out[2].depth_write_enabled==0u);
    CHECK(out[0].blend_enabled==0u);
    CHECK(out[1].blend_enabled==1u);
    CHECK(out[2].blend_enabled==1u);
    const uint32_t duplicate[3]={2u,1u,1u};
    const uint32_t out_of_range[3]={2u,1u,3u};
    const uint32_t too_early[3]={1u,2u,0u};
    const uint32_t far_at_end[3]={1u,0u,2u};
    memset(out,0xA5,sizeof(out));
    CHECK(foj_gpu_alpha_pass_contract(ranges,3,duplicate,3,out,3)==FOJ_GPU_ALPHA_PASS_INVALID);
    CHECK(retained(out));
    CHECK(foj_gpu_alpha_pass_contract(ranges,3,out_of_range,3,out,3)==FOJ_GPU_ALPHA_PASS_INVALID);
    CHECK(retained(out));
    CHECK(foj_gpu_alpha_pass_contract(ranges,3,too_early,3,out,3)==FOJ_GPU_ALPHA_PASS_UNSAFE);
    CHECK(retained(out));
    CHECK(foj_gpu_alpha_pass_contract(ranges,3,far_at_end,3,out,3)==FOJ_GPU_ALPHA_PASS_UNSAFE);
    CHECK(retained(out));
    FojGpuDrawRange malformed[3]={ranges[0],ranges[1],ranges[2]};
    malformed[2].material_index=1u;
    CHECK(foj_gpu_alpha_pass_contract(malformed,3,forward,3,out,3)==FOJ_GPU_ALPHA_PASS_INVALID);
    CHECK(retained(out));
    malformed[2]=ranges[2];
    malformed[1].first_vertex=4u;
    CHECK(foj_gpu_alpha_pass_contract(malformed,3,forward,3,out,3)==FOJ_GPU_ALPHA_PASS_INVALID);
    CHECK(retained(out));
    malformed[1]=ranges[1];
    malformed[0].vertex_count=6u;
    CHECK(foj_gpu_alpha_pass_contract(malformed,3,forward,3,out,3)==FOJ_GPU_ALPHA_PASS_INVALID);
    CHECK(retained(out));
    CHECK(foj_gpu_alpha_pass_contract(NULL,3,forward,3,out,3)==FOJ_GPU_ALPHA_PASS_INVALID);
    CHECK(foj_gpu_alpha_pass_contract(ranges,3,NULL,3,out,3)==FOJ_GPU_ALPHA_PASS_INVALID);
    CHECK(foj_gpu_alpha_pass_contract(ranges,3,forward,3,NULL,3)==FOJ_GPU_ALPHA_PASS_INVALID);
    CHECK(foj_gpu_alpha_pass_contract(ranges,2,forward,3,out,3)==FOJ_GPU_ALPHA_PASS_INVALID);
    CHECK(foj_gpu_alpha_pass_contract(ranges,3,forward,2,out,3)==FOJ_GPU_ALPHA_PASS_INVALID);
    CHECK(foj_gpu_alpha_pass_contract(ranges,3,forward,3,out,2)==FOJ_GPU_ALPHA_PASS_INVALID);
    CHECK(retained(out));
    printf("Stage274 native alpha state contract %u checks pass\n",checks);
    return 0;
}
