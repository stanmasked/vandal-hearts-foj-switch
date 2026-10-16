#define _POSIX_C_SOURCE 200809L
/* Entirely generated DKSH test data; never copies actual game shaders. */
#include "dksh_module.h"
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

static void put32(uint8_t *p,uint32_t n) {
    p[0]=(uint8_t)n;p[1]=(uint8_t)(n>>8);
    p[2]=(uint8_t)(n>>16);p[3]=(uint8_t)(n>>24);
}
static void fixture(uint8_t out[512],unsigned stage) {
    memset(out,0,512);
    put32(out,0x48534B44);
    put32(out+4,24);put32(out+8,256);put32(out+12,256);
    put32(out+16,24);put32(out+20,1);
    put32(out+24,stage);
    put32(out+28,0);
    put32(out+32,8); /* registers */
    memset(out+256,0xA5,256);
}
static void test_generated_metadata(void) {
    uint8_t data[512];
    fixture(data,FOJ_DKSH_VERTEX);
    assert(foj_dksh_validate(data,sizeof(data),FOJ_DKSH_VERTEX));
    assert(!foj_dksh_validate(data,sizeof(data),FOJ_DKSH_FRAGMENT));
    fixture(data,FOJ_DKSH_FRAGMENT);
    assert(foj_dksh_validate(data,sizeof(data),FOJ_DKSH_FRAGMENT));
    assert(!foj_dksh_validate(data,511,FOJ_DKSH_FRAGMENT));
    assert(!foj_dksh_validate(NULL,512,FOJ_DKSH_VERTEX));
    put32(data+16,224); /* table record straddles control/code */
    assert(!foj_dksh_validate(data,512,FOJ_DKSH_FRAGMENT));
    put32(data+16,24);
    put32(data+28,256); /* entrypoint past code */
    assert(!foj_dksh_validate(data,512,FOJ_DKSH_FRAGMENT));
    put32(data+28,0);
    put32(data+36,255);put32(data+40,4); /* invalid constbuf */
    assert(!foj_dksh_validate(data,512,FOJ_DKSH_FRAGMENT));
    put32(data+36,0);put32(data+40,0);
    put32(data+24,9); /* unknown stage */
    assert(!foj_dksh_validate(data,512,FOJ_DKSH_FRAGMENT));
}
static void test_user_local_file_loader(void) {
    uint8_t sample[512],loaded[1024]={0};
    fixture(sample,FOJ_DKSH_VERTEX);
    char path[]="/tmp/foj_generated_shader_XXXXXX";
    int fd=mkstemp(path);
    assert(fd>=0);
    FILE *file=fdopen(fd,"wb");
    assert(file);
    assert(fwrite(sample,1,sizeof(sample),file)==sizeof(sample));
    assert(fclose(file)==0);
    size_t count=99;
    assert(foj_dksh_read_file(path,loaded,sizeof(loaded),
                              FOJ_DKSH_VERTEX,&count));
    assert(count==sizeof(sample));
    assert(!memcmp(sample,loaded,sizeof(sample)));
    assert(!foj_dksh_read_file(path,loaded,sizeof(loaded),
                               FOJ_DKSH_FRAGMENT,&count));
    assert(!foj_dksh_read_file(path,loaded,300,
                               FOJ_DKSH_VERTEX,&count));
    assert(unlink(path)==0);
    assert(!foj_dksh_read_file(path,loaded,sizeof(loaded),
                               FOJ_DKSH_VERTEX,&count));
}
int main(void) {
    test_generated_metadata();
    test_user_local_file_loader();
    puts("DKSH: verified generated vertex/fragment stage and private-file bounds");
    return 0;
}
