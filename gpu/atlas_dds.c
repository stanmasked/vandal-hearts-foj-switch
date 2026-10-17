#include "atlas_dds.h"
#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static uint32_t little32(const uint8_t *p) {
    return (uint32_t)p[0] | ((uint32_t)p[1]<<8) |
           ((uint32_t)p[2]<<16) | ((uint32_t)p[3]<<24);
}
int foj_atlas_dds_decode(const uint8_t *dds,size_t len,
                         uint8_t *out,size_t cap,FojAtlasRgba8Info *info) {
    if (!dds||!out||!info)return 0;
    if (len<FOJ_ATLAS_DDS_HEADER_BYTES||
        memcmp(dds,"DDS ",4)!=0||little32(dds+4)!=124 ||
        (little32(dds+8)&0x100fU)!=0x100fU ||
        little32(dds+76)!=32 || little32(dds+80)!=0x41 ||
        little32(dds+84)!=0 || little32(dds+88)!=32 ||
        little32(dds+92)!=0x000000ffU ||
        little32(dds+96)!=0x0000ff00U ||
        little32(dds+100)!=0x00ff0000U ||
        little32(dds+104)!=0xff000000U ||
        (little32(dds+108)&0x1000U)==0 ||
        little32(dds+112)!=0 || little32(dds+116)!=0 ||
        little32(dds+120)!=0 || little32(dds+124)!=0)
        return 0;
    const uint32_t width=little32(dds+16),height=little32(dds+12);
    if (width<8||width>FOJ_ATLAS_MAX_WIDTH||width%8||
        !height||height>FOJ_ATLAS_MAX_HEIGHT ||
        little32(dds+24)!=0 || little32(dds+28)>1)
        return 0;
    const size_t bytes=(size_t)width*(size_t)height*4u;
    if (little32(dds+20)!=width*4u ||
        len!=FOJ_ATLAS_DDS_HEADER_BYTES+bytes || cap<bytes)
        return 0;
    memcpy(out,dds+FOJ_ATLAS_DDS_HEADER_BYTES,bytes);
    *info=(FojAtlasRgba8Info){width,height,bytes};
    return 1;
}

int foj_atlas_dds_try_read(const char *path,uint8_t *out,size_t cap,
                           FojAtlasRgba8Info *info) {
    if (!path||!out||!info)return -1;
    FILE *fp=fopen(path,"rb");
    if (!fp)return errno==ENOENT?0:-1;
    int result=-1;
    uint8_t *blob=NULL;
    if (fseek(fp,0,SEEK_END)!=0)goto done;
    long file_size=ftell(fp);
    if (file_size<0 || (unsigned long)file_size>
          (unsigned long)(FOJ_ATLAS_DDS_HEADER_BYTES+FOJ_ATLAS_MAX_BYTES))
        goto done;
    if (fseek(fp,0,SEEK_SET)!=0)goto done;
    blob=(uint8_t*)malloc((size_t)file_size+1);
    if (!blob)goto done;
    if (fread(blob,1,(size_t)file_size,fp)!=(size_t)file_size)
        goto done;
    if (!foj_atlas_dds_decode(blob,(size_t)file_size,out,cap,info))
        goto done;
    result=1;
done:
    free(blob);
    fclose(fp);
    return result;
}
