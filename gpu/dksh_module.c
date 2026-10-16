#include "dksh_module.h"
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static uint32_t u32le(const uint8_t *p) {
    return (uint32_t)p[0]|((uint32_t)p[1]<<8)|
           ((uint32_t)p[2]<<16)|((uint32_t)p[3]<<24);
}
int foj_dksh_validate(const void *buffer,size_t length,uint32_t stage) {
    if (!buffer || length<256 || length>FOJ_DKSH_MAX_BYTES ||
        (stage!=FOJ_DKSH_VERTEX && stage!=FOJ_DKSH_FRAGMENT))
        return 0;
    const uint8_t *p=(const uint8_t*)buffer;
    uint32_t magic=u32le(p),hdr=u32le(p+4),ctrl=u32le(p+8);
    uint32_t code=u32le(p+12),offset=u32le(p+16),count=u32le(p+20);
    if (magic!=UINT32_C(0x48534B44) || hdr!=24 ||
        ctrl<256 || (ctrl&255) || !code || (code&255) ||
        (uint64_t)ctrl+code!=length || count!=1 ||
        offset<24 || (offset&3) ||
        (uint64_t)offset+64>ctrl)
        return 0;
    const uint8_t *prog=p+offset;
    uint32_t type=u32le(prog);
    uint32_t entry=u32le(prog+4),cb_off=u32le(prog+12);
    uint32_t cb_size=u32le(prog+16);
    if(type!=stage || entry>=code) return 0;
    if(cb_size && (cb_off>=code || cb_size>code-cb_off))return 0;
    return 1;
}

int foj_dksh_read_file(const char *path,void *dst,size_t capacity,
                       uint32_t stage,size_t *bytes_written) {
    if(!path||!dst||!bytes_written || capacity<256 ||
       (stage!=FOJ_DKSH_VERTEX && stage!=FOJ_DKSH_FRAGMENT))
        return 0;
    if(capacity>FOJ_DKSH_MAX_BYTES)capacity=FOJ_DKSH_MAX_BYTES;
    FILE *file=fopen(path,"rb");
    if(!file)return 0;
    int valid=0;
    if(fseek(file,0,SEEK_END)==0) {
        long length=ftell(file);
        if(length>=256 && (size_t)length<=capacity &&
           fseek(file,0,SEEK_SET)==0) {
            /* Validate untrusted SD data before touching live GPU memory. */
            const size_t n=(size_t)length;
            uint8_t *tmp=(uint8_t*)malloc(n);
            if(tmp) {
                if(fread(tmp,1,n,file)==n &&
                   foj_dksh_validate(tmp,n,stage)) {
                    memcpy(dst,tmp,n);
                    *bytes_written=n;
                    valid=1;
                }
                free(tmp);
            }
        }
    }
    fclose(file);
    return valid;
}
