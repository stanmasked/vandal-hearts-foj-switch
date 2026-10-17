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

    put32(dest,4,0xe4e4e4e4u);
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
    const uint64_t special=(6ull)|(7ull<<3)|(2ull<<6)|(3ull<<9);
    for(unsigned k=0;k<6;++k)
        first[2+k]=(uint8_t)(special>>(8u*k));
    assert(foj_atlas_dds_decode(data,bc3len,pixels,sizeof(pixels),&info));
    assert(pixels[3]==0 && pixels[7]==255);
    assert(pixels[11]==20 && pixels[15]==40);
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


static void make_mips(uint8_t *data,unsigned count,int bc) {
    put32(data,28,count);
    put32(data,8,(bc?0x81007u:0x100fu)|0x20000u);
    put32(data,108,0x401008u);
}
static void test_bgra_and_mips(void) {
    uint8_t data[FOJ_ATLAS_DDS_HEADER_BYTES+FOJ_ATLAS_MAX_INPUT_BYTES];
    uint8_t out[FOJ_ATLAS_MAX_BYTES];
    FojAtlasRgba8Info info={0};

    /* BGRA bytes 11/22/33/44 become RGBA 33/22/11/44. */
    make_header(data,8,8);
    put32(data,92,0x00ff0000u);
    put32(data,100,0x000000ffu);
    for (unsigned i=0;i<256;i+=4) {
        data[128+i]=11;data[128+i+1]=22;
        data[128+i+2]=33;data[128+i+3]=44;
    }
    const size_t base_len=128+256;
    memset(out,0xa5,sizeof(out));
    assert(foj_atlas_dds_decode(data,base_len,out,sizeof(out),&info));
    assert(info.pixel_bytes==256 && info.width==8 && info.height==8);
    for (unsigned i=0;i<256;i+=4) {
        assert(out[i]==33 && out[i+1]==22);
        assert(out[i+2]==11 && out[i+3]==44);
    }
    /* Wrong channel layout or partial payload must preserve output. */
    memset(out,0xa5,sizeof(out));
    info=(FojAtlasRgba8Info){4,5,6};
    put32(data,92,0x0000ff00u);
    expect_bad(data,base_len,out,&info);
    put32(data,92,0x00ff0000u);
    expect_bad(data,base_len-1,out,&info);
    expect_bad(data,base_len+1,out,&info);

    /* RGBA8: 8x8 -> 4x4 -> 2x2 -> 1x1, with only base decoded. */
    make_header(data,8,8);
    make_mips(data,4,0);
    const size_t rgba_tail=64+16+4;
    const size_t rgba_len=128+256+rgba_tail;
    memset(data+128,0x34,256);
    memset(data+128+256,0x91,rgba_tail);
    memset(out,0xa5,sizeof(out));
    assert(foj_atlas_dds_decode(data,rgba_len,out,sizeof(out),&info));
    for(size_t i=0;i<256;++i)assert(out[i]==0x34);
    assert(out[256]==0xa5);
    memset(out,0xa5,sizeof(out));
    info=(FojAtlasRgba8Info){4,5,6};
    expect_bad(data,rgba_len-1,out,&info);
    expect_bad(data,rgba_len+1,out,&info);
    put32(data,28,5);expect_bad(data,rgba_len,out,&info);
    put32(data,28,4);
    put32(data,108,0x1000u);expect_bad(data,rgba_len,out,&info);
    put32(data,108,0x401008u);
    put32(data,8,0x100fu);expect_bad(data,rgba_len,out,&info);
    put32(data,8,0x2100fu);
    put32(data,20,32); /* correct base-level pitch */
    assert(foj_atlas_dds_decode(data,rgba_len,out,sizeof(out),&info));

    /* BC1/DXT1 full mip chain: 32 + 8 + 8 + 8 compressed bytes. */
    make_bc_header(data,8,8,0);
    make_mips(data,4,1);
    for (unsigned i=0;i<4;++i)
        fill_bc1(data+128+i*8u,0xf800u,0x07e0u);
    const size_t bc1_total=32+8+8+8;
    memset(data+128+32,0,bc1_total-32);
    assert(foj_atlas_dds_decode(data,128+bc1_total,out,sizeof(out),&info));
    assert(info.pixel_bytes==256 && out[0]==255 && out[3]==255);
    memset(out,0xa5,sizeof(out));
    info=(FojAtlasRgba8Info){4,5,6};
    expect_bad(data,128+bc1_total-1,out,&info);
    expect_bad(data,128+bc1_total+1,out,&info);
    put32(data,20,24);expect_bad(data,128+bc1_total,out,&info);
    put32(data,20,32);
    put32(data,12,9);expect_bad(data,128+bc1_total,out,&info);
    put32(data,12,8);

    /* BC3/DXT5: four full-res blocks plus three 16-byte mip blocks. */
    make_bc_header(data,8,8,1);
    make_mips(data,4,1);
    for (unsigned i=0;i<4;++i) {
        uint8_t *block=data+128+i*16u;
        memset(block,0,16);
        block[0]=255;block[1]=0;
        fill_bc1(block+8,0xf800u,0x07e0u);
    }
    const size_t bc3_total=64+16+16+16;
    memset(data+128+64,0,bc3_total-64);
    assert(foj_atlas_dds_decode(data,128+bc3_total,out,sizeof(out),&info));
    assert(info.pixel_bytes==256 && out[0]==255 && out[3]==255);

    /* Upper bound: all nine levels of a 256x256 RGBA8 DDS. */
    make_header(data,256,256);
    make_mips(data,9,0);
    size_t cursor=128;
    for(unsigned w=256,h=256,level=0;level<9;++level) {
        size_t level_bytes=(size_t)w*h*4;
        memset(data+cursor,level?0x91:0x41,level_bytes);
        cursor+=level_bytes;
        if(w>1)w/=2;
        if(h>1)h/=2;
    }
    assert(cursor<=sizeof(data));
    memset(out,0xa5,sizeof(out));
    assert(foj_atlas_dds_decode(data,cursor,out,sizeof(out),&info));
    assert(info.width==256 && info.height==256);
    assert(info.pixel_bytes==FOJ_ATLAS_MAX_BYTES);
    assert(out[0]==0x41 && out[FOJ_ATLAS_MAX_BYTES-1]==0x41);
    expect_bad(data,cursor-1,out,&info);
    /* A legal max-size mip file can pass the bounded file intake too. */
    const char *path="build/foj-synthetic-mip-chain.dds";
    FILE *fp=fopen(path,"wb");
    assert(fp);
    assert(fwrite(data,1,cursor,fp)==cursor);
    assert(fclose(fp)==0);
    assert(foj_atlas_dds_try_read(path,out,sizeof(out),&info)==1);
    assert(out[0]==0x41);
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
    test_bgra_and_mips();
    puts("Private RGBA8/BGRA8/BC1/BC3 DDS + complete mip-chain intake: PASS");
    return 0;
}
