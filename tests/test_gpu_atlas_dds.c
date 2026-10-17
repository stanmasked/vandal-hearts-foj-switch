/* SDK-free synthetic classic DDS RGBA8 parser and file regression. */
#ifdef NDEBUG
#undef NDEBUG
#endif
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "atlas_dds.h"

static void put32(uint8_t *buf,unsigned offset,uint32_t v) {
    buf[offset]=(uint8_t)v;
    buf[offset+1]=(uint8_t)(v>>8);
    buf[offset+2]=(uint8_t)(v>>16);
    buf[offset+3]=(uint8_t)(v>>24);
}
static void make_header(uint8_t *blob,unsigned width,unsigned height) {
    memset(blob,0,FOJ_ATLAS_DDS_HEADER_BYTES);
    memcpy(blob,"DDS ",4);
    put32(blob,4,124);
    put32(blob,8,0x100f);
    put32(blob,12,height);
    put32(blob,16,width);
    put32(blob,20,width*4);
    put32(blob,28,1);
    put32(blob,76,32);
    put32(blob,80,0x41);
    put32(blob,88,32);
    put32(blob,92,0xff);
    put32(blob,96,0xff00);
    put32(blob,100,0xff0000);
    put32(blob,104,0xff000000u);
    put32(blob,108,0x1000);
}
static void expect_bad(uint8_t *blob,size_t n,uint8_t *out,
                       FojAtlasRgba8Info *info) {
    uint8_t saved[128];
    FojAtlasRgba8Info saved_info=*info;
    memcpy(saved,out,sizeof(saved));
    assert(!foj_atlas_dds_decode(blob,n,out,128,info));
    assert(!memcmp(saved,out,sizeof(saved)));
    assert(!memcmp(&saved_info,info,sizeof(saved_info)));
}
int main(void) {
    uint8_t data[FOJ_ATLAS_DDS_HEADER_BYTES+FOJ_ATLAS_MAX_BYTES];
    uint8_t out[FOJ_ATLAS_MAX_BYTES];
    FojAtlasRgba8Info info={4,5,6};
    make_header(data,8,8);
    const size_t len=FOJ_ATLAS_DDS_HEADER_BYTES+8*8*4;
    for(size_t i=FOJ_ATLAS_DDS_HEADER_BYTES;i<len;++i)
        data[i]=(uint8_t)(i*7+1);
    memset(out,0xa5,sizeof(out));
    assert(foj_atlas_dds_decode(data,len,out,sizeof(out),&info));
    assert(info.width==8 && info.height==8 && info.pixel_bytes==256);
    assert(!memcmp(out,data+FOJ_ATLAS_DDS_HEADER_BYTES,256));
    memset(out,0xa5,sizeof(out));
    info=(FojAtlasRgba8Info){4,5,6};

    expect_bad(data,len-1,out,&info);
    expect_bad(data,len+1,out,&info);
    assert(!foj_atlas_dds_decode(data,len,NULL,sizeof(out),&info));
    assert(!foj_atlas_dds_decode(data,len,out,sizeof(out),NULL));
    assert(!foj_atlas_dds_decode(data,len,out,255,&info));
    /* Small pixel count with insufficient pitch and other invalid formats. */
    const unsigned offsets[]={0,4,8,12,16,20,24,28,76,80,84,88,
                              92,96,100,104,108,112,116,120,124};
    for(size_t i=0;i<sizeof(offsets)/sizeof(offsets[0]);++i){
        unsigned off=offsets[i];
        uint8_t old[4];memcpy(old,data+off,4);
        if(off==0)memcpy(data,"DX10",4);
        else put32(data,off,0xffffffffu);
        expect_bad(data,len,out,&info);
        memcpy(data+off,old,4);
    }
    put32(data,16,10);expect_bad(data,len,out,&info);put32(data,16,8);
    put32(data,16,257);expect_bad(data,len,out,&info);put32(data,16,8);
    put32(data,28,2);expect_bad(data,len,out,&info);put32(data,28,1);
    assert(foj_atlas_dds_decode(data,len,out,sizeof(out),&info));

    /* Exercise a maximum legal atlas, and guard against out-of-range files. */
    make_header(data,256,256);
    const size_t big_len=FOJ_ATLAS_DDS_HEADER_BYTES+FOJ_ATLAS_MAX_BYTES;
    memset(data+FOJ_ATLAS_DDS_HEADER_BYTES,0x65,FOJ_ATLAS_MAX_BYTES);
    assert(foj_atlas_dds_decode(data,big_len,out,sizeof(out),&info));
    assert(info.width==256 && info.height==256);
    assert(out[0]==0x65 && out[FOJ_ATLAS_MAX_BYTES-1]==0x65);

    /* Local file input, including absent and corrupted file behavior. */
    const char *path="build/foj-synthetic-atlas-test.dds";
    assert(foj_atlas_dds_try_read("build/foj-synthetic-missing-atlas.dds",
                                  out,sizeof(out),&info)==0);
    make_header(data,8,8);
    FILE *file=fopen(path,"wb");
    assert(file);
    assert(fwrite(data,1,len,file)==len);
    assert(fclose(file)==0);
    assert(foj_atlas_dds_try_read(path,out,sizeof(out),&info)==1);
    assert(info.width==8 && info.height==8);
    file=fopen(path,"wb");
    assert(file);
    assert(fwrite("invalid",1,7,file)==7);
    assert(fclose(file)==0);
    memset(out,0xa5,sizeof(out));
    info=(FojAtlasRgba8Info){4,5,6};
    assert(foj_atlas_dds_try_read(path,out,sizeof(out),&info)==-1);
    assert(out[0]==0xa5 && out[255]==0xa5);
    assert(info.width==4 && info.height==5 && info.pixel_bytes==6);
    assert(remove(path)==0);
    puts("Private RGBA8 DDS atlas bounds, flags, file intake: PASS");
    return 0;
}
