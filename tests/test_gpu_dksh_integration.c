#define _POSIX_C_SOURCE 200809L
/* Synthetic two-stage shader memory integration test. No game resources. */
#include "dksh_module.h"
#include "shader_layout.h"
/* The test intentionally uses assertions with side effects (I/O, loader calls).
 * Never compile them away when a caller supplies -DNDEBUG. */
#ifdef NDEBUG
#undef NDEBUG
#endif
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

static void le32(uint8_t *p, uint32_t v) {
    p[0]=(uint8_t)v; p[1]=(uint8_t)(v>>8);
    p[2]=(uint8_t)(v>>16); p[3]=(uint8_t)(v>>24);
}
static void generated_module(uint8_t *p, size_t n, uint32_t stage) {
    assert(n>=512 && n<=FOJ_DKSH_MAX_BYTES && n%256==0);
    memset(p,0,n);
    le32(p,0x48534B44); le32(p+4,24);
    le32(p+8,256); le32(p+12,(uint32_t)(n-256));
    le32(p+16,24); le32(p+20,1);
    le32(p+24,stage); le32(p+28,0);
    memset(p+256,0xA5,n-256);
}
static void write_module(const char *path,const uint8_t *p,size_t n) {
    FILE *f=fopen(path,"wb"); assert(f);
    assert(fwrite(p,1,n,f)==n);
    assert(fclose(f)==0);
}
int main(void) {
    const size_t max=FOJ_GPU_SHADER_MAX_DKSH;
    assert(max==FOJ_DKSH_MAX_BYTES);
    FojGpuShaderLayout layout;
    assert(foj_gpu_shader_layout(max,max,&layout));
    assert(layout.fragment_offset>=layout.vertex_offset+layout.vertex_size);
    assert(layout.fragment_offset+layout.fragment_size<=layout.protected_tail_start);
    assert(layout.protected_tail_start<=layout.block_size);

    uint8_t *pool=malloc(FOJ_GPU_SHADER_CODE_POOL);
    uint8_t *module=malloc(max);
    assert(pool && module);
    memset(pool,0xCC,FOJ_GPU_SHADER_CODE_POOL);
    char path[]="/tmp/foj_dksh_slots_XXXXXX";
    int fd=mkstemp(path); assert(fd>=0);
    assert(close(fd)==0);
    size_t used=0;
    generated_module(module,max,FOJ_DKSH_VERTEX);
    write_module(path,module,max);
    assert(foj_dksh_read_file(path,pool+layout.vertex_offset,
                              FOJ_GPU_SHADER_SLOT_BYTES,
                              FOJ_DKSH_VERTEX,&used));
    assert(used==max);
    generated_module(module,max,FOJ_DKSH_FRAGMENT);
    write_module(path,module,max);
    assert(foj_dksh_read_file(path,pool+layout.fragment_offset,
                              FOJ_GPU_SHADER_SLOT_BYTES,
                              FOJ_DKSH_FRAGMENT,&used));
    assert(used==max);
    for(size_t i=max;i<layout.fragment_offset;++i)assert(pool[i]==0xCC);
    for(size_t i=layout.fragment_offset+max;i<layout.block_size;++i)
        assert(pool[i]==0xCC);

    /* Correct metadata for the wrong stage must also preserve the slot. */
    generated_module(module,max,FOJ_DKSH_VERTEX);
    write_module(path,module,max);
    used=777;
    assert(!foj_dksh_read_file(path,pool+layout.fragment_offset,
                               FOJ_GPU_SHADER_SLOT_BYTES,
                               FOJ_DKSH_FRAGMENT,&used));
    assert(used==777);
    generated_module(module,max,FOJ_DKSH_FRAGMENT);
    assert(memcmp(pool+layout.fragment_offset,module,max)==0);
    for(size_t i=layout.fragment_offset+max;i<layout.block_size;++i)
        assert(pool[i]==0xCC);

    /* Invalid replacement must not change the already loaded fragment. */
    module[0]=0;
    write_module(path,module,max);
    used=123;
    assert(!foj_dksh_read_file(path,pool+layout.fragment_offset,
                               FOJ_GPU_SHADER_SLOT_BYTES,
                               FOJ_DKSH_FRAGMENT,&used));
    assert(used==123);
    /* Check exact original bytes instead of relying on header patterns. */
    generated_module(module,max,FOJ_DKSH_FRAGMENT);
    assert(memcmp(pool+layout.fragment_offset,module,max)==0);
    /* Both failed fragment updates must preserve the vertex slot as well. */
    generated_module(module,max,FOJ_DKSH_VERTEX);
    assert(memcmp(pool+layout.vertex_offset,module,max)==0);
    for(size_t i=max;i<layout.fragment_offset;++i)
        assert(pool[i]==0xCC);
    for(size_t i=layout.fragment_offset+max;i<layout.block_size;++i)
        assert(pool[i]==0xCC);
    /* Truncated file must preserve both loaded stages and output count. */
    generated_module(module,max,FOJ_DKSH_FRAGMENT);
    write_module(path,module,128);
    used=456;
    assert(!foj_dksh_read_file(path,pool+layout.fragment_offset,
                               FOJ_GPU_SHADER_SLOT_BYTES,
                               FOJ_DKSH_FRAGMENT,&used));
    assert(used==456);
    generated_module(module,max,FOJ_DKSH_FRAGMENT);
    assert(memcmp(pool+layout.fragment_offset,module,max)==0);
    generated_module(module,max,FOJ_DKSH_VERTEX);
    assert(memcmp(pool+layout.vertex_offset,module,max)==0);

    /* A valid maximum-size module cannot fit into a smaller input slot. */
    generated_module(module,max,FOJ_DKSH_FRAGMENT);
    write_module(path,module,max);
    used=789;
    assert(!foj_dksh_read_file(path,pool+layout.fragment_offset,
                               max-256,FOJ_DKSH_FRAGMENT,&used));
    assert(used==789);
    assert(memcmp(pool+layout.fragment_offset,module,max)==0);
    generated_module(module,max,FOJ_DKSH_VERTEX);
    assert(memcmp(pool+layout.vertex_offset,module,max)==0);
    /* Oversized file must be rejected before allocating/copying GPU data. */
    uint8_t *oversize=(uint8_t*)malloc(max+256);
    assert(oversize);
    generated_module(oversize,max,FOJ_DKSH_FRAGMENT);
    memset(oversize+max,0x5A,256);
    write_module(path,oversize,max+256);
    free(oversize);
    used=890;
    assert(!foj_dksh_read_file(path,pool+layout.fragment_offset,
                               FOJ_GPU_SHADER_SLOT_BYTES,
                               FOJ_DKSH_FRAGMENT,&used));
    assert(used==890);
    generated_module(module,max,FOJ_DKSH_FRAGMENT);
    assert(memcmp(pool+layout.fragment_offset,module,max)==0);
    generated_module(module,max,FOJ_DKSH_VERTEX);
    assert(memcmp(pool+layout.vertex_offset,module,max)==0);
    /* Invalid input pointers/stages must be rejected without touching slots. */
    generated_module(module,max,FOJ_DKSH_FRAGMENT);
    used=901;
    assert(!foj_dksh_read_file(NULL,pool+layout.fragment_offset,
                               max,FOJ_DKSH_FRAGMENT,&used));
    assert(!foj_dksh_read_file(path,NULL,max,FOJ_DKSH_FRAGMENT,&used));
    assert(!foj_dksh_read_file(path,pool+layout.fragment_offset,
                               max,FOJ_DKSH_FRAGMENT,NULL));
    assert(!foj_dksh_read_file(path,pool+layout.fragment_offset,
                               max,UINT32_MAX,&used));
    assert(!foj_dksh_read_file(path,pool+layout.fragment_offset,
                               255,FOJ_DKSH_FRAGMENT,&used));
    assert(used==901);
    assert(memcmp(pool+layout.fragment_offset,module,max)==0);
    generated_module(module,max,FOJ_DKSH_VERTEX);
    assert(memcmp(pool+layout.vertex_offset,module,max)==0);
    assert(unlink(path)==0);
    /* Missing file after removal must also leave the loaded shaders intact. */
    used=902;
    assert(!foj_dksh_read_file(path,pool+layout.fragment_offset,
                               max,FOJ_DKSH_FRAGMENT,&used));
    assert(used==902);
    generated_module(module,max,FOJ_DKSH_FRAGMENT);
    assert(memcmp(pool+layout.fragment_offset,module,max)==0);
    generated_module(module,max,FOJ_DKSH_VERTEX);
    assert(memcmp(pool+layout.vertex_offset,module,max)==0);
    free(module);
    free(pool);
    puts("DKSH two-slot transactional integration: PASS");
    return 0;
}
