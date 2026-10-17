/* SDK-free synthetic classic DDS RGBA8, BC1 and BC3 regression. */
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
static void put16(uint8_t *buf,uint16_t v) {
    buf[0]=(uint8_t)v;
    buf[1]=(uint8_t)(v>>8);
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
    uint8_t saved[FOJ_ATLAS_MAX_BYTES];
    FojAtlasRgba8Info saved_info=*info;
    memcpy(saved,out,sizeof(saved));
    assert(!foj_atlas_dds_decode(blob,n,out,FOJ_ATLAS_MAX_BYTES,info));
    assert(!memcmp(saved,out,sizeof(saved)));
    assert(!memcmp(&saved_info,info,sizeof(saved_info)));
}

static void make_bc_header(uint8_t *blob,unsigned w,unsigned h,int bc3) {
    make_header(blob,w,h);
    put32(blob,8,0x81007U);
    put32(blob,20,(w/4u)*(h/4u)*(bc3?16u:8u));
    put32(blob,80,4);
    put32(blob,84,bc3?0x35545844u:0x31545844u);
    put32(blob,88,0);
    put32(blob,92,0);
    put32(blob,96,0);
    put32(blob,100,0);
    put32(blob,104,0);
}
static void fill_bc1(uint8_t *dest,uint16_t c0,uint16_t c1) {
    put16(dest,c0);
    put16(dest+2,c1);
    /* Four texels per row use palette indexes 0,1,2,3. */
    put32(dest,0); /* overwritten below with the full block layout */
    put16(dest,c0);
    put16(dest+2,c1);
    put32(dest+4,0xe4e4e4e4u);
}
static void test_bcn(void) {
    uint8_t data[FOJ_ATLAS_DDS_HEADER_BYTES+256];
    uint8_t pixels[FOJ_ATLAS_MAX_BYTES];
    FojAtlasRgba8Info info={0};
    make_bc_header(data,8,8,0);
    for(unsigned i=0;i<4;++i)
        fill_bc1(data+FOJ_ATLAS_DDS_HEADER_BYTES+i*8u,0xf800u,0x07e0u);
    const size_t bc1len=FOJ_ATLAS_DDS_HEADER_BYTES+32;
    memset(pixels,0xa5,sizeof(pixels));
    assert(foj_atlas_dds_decode(data,bc1len,pixels,sizeof(pixels),&info));
    assert(info.width==8 && info.height==8 && info.pixel_bytes==256);
    const uint8_t expected[4][4]={
        {255,0,0,255}, {0,255,0,255},
        {170,85,0,255}, {85,170,0,255}
    };
    for(unsigned x=0;x<8;++x) {
        assert(!memcmp(pixels+x*4,expected[x%4],4));
        assert(!memcmp(pixels+(4*8+x)*4,expected[x%4],4));
    }
    /* BC1 endpoint reversal enables 3-color mode and transparent #3. */
    fill_bc1(data+FOJ_ATLAS_DDS_HEADER_BYTES,0x07e0u,0xf800u);
    assert(foj_atlas_dds_decode(data,bc1len,pixels,sizeof(pixels),&info));
    assert(pixels[0]==0 && pixels[1]==255 && pixels[3]==255);
    assert(pixels[2*4]==127 && pixels[2*4+1]==127);
    assert(pixels[3*4+3]==0);
    assert(pixels[4*4+3]==255);

    /* Headers are checked BEFORE writing even the first decompressed block. */
    memset(pixels,0xa5,sizeof(pixels));
    info=(FojAtlasRgba8Info){4,5,6};
    expect_bad(data,bc1len-1,pixels,&info);
    expect_bad(data,bc1len+1,pixels,&info);
    put32(data,84,0x33545844u); /* DXT3/BC2 is unsupported. */
    expect_bad(data,bc1len,pixels,&info);
    put32(data,84,0x30315844u); /* DX10 extended header. */
    expect_bad(data,bc1len,pixels,&info);
    put32(data,84,0x31545844u);
    put32(data,8,0x100fU);expect_bad(data,bc1len,pixels,&info);
    put32(data,8,0x81007U);
    put32(data,20,0);expect_bad(data,bc1len,pixels,&info);
    put32(data,20,32);
    put32(data,12,7);expect_bad(data,bc1len,pixels,&info);
    put32(data,12,8);
    put32(data,28,2);expect_bad(data,bc1len,pixels,&info);
    put32(data,28,1);
    put32(data,88,32);expect_bad(data,bc1len,pixels,&info);
    put32(data,88,0);
    assert(foj_atlas_dds_decode(data,bc1len,pixels,sizeof(pixels),&info));

    /* DXT5/BC3: alpha has its own 48-bit 3-bit-index block. */
    make_bc_header(data,8,8,1);
    for(unsigned i=0;i<4;++i) {
        uint8_t *block=data+FOJ_ATLAS_DDS_HEADER_BYTES+i*16u;
        memset(block,0,16);
        block[0]=200;block[1]=100;
        const uint64_t alpha_indices=(1ull<<3)|(2ull<<6)|(7ull<<9);
        for(unsigned k=0;k<6;++k)
            block[2+k]=(uint8_t)(alpha_indices>>(8u*k));
        fill_bc1(block+8,0x07e0u,0xf800u);
    }
    const size_t bc3len=FOJ_ATLAS_DDS_HEADER_BYTES+64;
    assert(foj_atlas_dds_decode(data,bc3len,pixels,sizeof(pixels),&info));
    assert(pixels[0]==0 && pixels[1]==255 && pixels[3]==200);
    assert(pixels[4]==255 && pixels[5]==0 && pixels[7]==100);
    assert(pixels[8]==85 && pixels[9]==170 && pixels[11]==185);
    assert(pixels[12]==170 && pixels[13]==85 && pixels[15]==114);
    /* BC3 color palette always has four entries, even when c0<c1. */
    /* Alpha a0<=a1 adds explicit zero/255 entries at indexes 6 and 7. */
    uint8_t *first=data+FOJ_ATLAS_DDS_HEADER_BYTES;
    first[0]=0;first[1]=100;
    const uint64_t special=(6ull)|(7ull<<3);
    for(unsigned k=0;k<6;++k)
        first[2+k]=(uint8_t)(special>>(8u*k));
    assert(foj_atlas_dds_decode(data,bc3len,pixels,sizeof(pixels),&info));
    assert(pixels[3]==0 && pixels[7]==255);
    assert(pixels[11]==80); /* (4*0 + 1*100)/5? index 2 = 20; index 0 = 0 */
    /* Rejection is transactional for truncated BC3 data as well. */
    memset(pixels,0xa5,sizeof(pixels));
    info=(FojAtlasRgba8Info){4,5,6};
    expect_bad(data,bc3len-1,pixels,&info);
    expect_bad(data,bc3len+1,pixels,&info);
    assert(foj_atlas_dds_decode(data,bc3len,pixels,sizeof(pixels),&info));

    /* Compressed file path must decode into RGBA pixels, not copied blocks. */
    const char *path="build/foj-synthetic-atlas-bc3-test.dds";
    FILE *fp=fopen(path,"wb");
    assert(fp);
    assert(fwrite(data,1,bc3len,fp)==bc3len);
    assert(fclose(fp)==0);
    assert(foj_atlas_dds_try_read(path,pixels,sizeof(pixels),&info)==1);
    assert(info.width==8 && info.height==8 && info.pixel_bytes==256);
    assert(pixels[3]==0 && pixels[7]==255);
    assert(remove(path)==0);
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
    test_bcn();
    puts("Private RGBA8/BC1/BC3 DDS atlas decode, alpha and bounds: PASS");
    return 0;
}
