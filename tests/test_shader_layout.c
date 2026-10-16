#include "shader_layout.h"
#include <assert.h>
#include <stdio.h>
#include <stdint.h>

int main(void) {
    FojGpuShaderLayout out={7,8,9,10,11,12};
    assert(foj_gpu_shader_layout(512,512,&out));
    assert(out.block_size==262144 && out.vertex_offset==0);
    assert(out.fragment_offset==131072 && out.protected_tail_start==261120);
    assert(out.vertex_size==512 && out.fragment_size==512);
    assert(foj_gpu_shader_layout(126976,126976,&out));
    assert((size_t)out.fragment_offset + out.fragment_size == 258048);
    assert(out.fragment_offset + out.fragment_size < out.protected_tail_start);
    FojGpuShaderLayout before=out;
    assert(!foj_gpu_shader_layout(126977,512,&out));
    assert(!foj_gpu_shader_layout(126720,511,&out));
    assert(!foj_gpu_shader_layout(256,512,&out));
    assert(!foj_gpu_shader_layout(0,512,&out));
    assert(!foj_gpu_shader_layout(512,(size_t)UINT32_MAX+1u,&out));
    assert(!foj_gpu_shader_layout(512,512,NULL));
    assert(out.fragment_size==before.fragment_size);
    assert(out.protected_tail_start==before.protected_tail_start);
    puts("GPU shader slots: offsets, 1KiB tail, 256-byte alignment and rollback PASS");
    return 0;
}
