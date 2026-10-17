#include "atlas_dds.h"
#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

enum {
    FOJ_DDS_DXT1 = 0x31545844u,
    FOJ_DDS_DXT5 = 0x35545844u
};

static uint16_t little16(const uint8_t *p) {
    return (uint16_t)((uint16_t)p[0] | ((uint16_t)p[1]<<8));
}
static uint32_t little32(const uint8_t *p) {
    return (uint32_t)p[0] | ((uint32_t)p[1]<<8) |
           ((uint32_t)p[2]<<16) | ((uint32_t)p[3]<<24);
}
static void unpack565(uint16_t v,uint8_t rgba[4]) {
    const unsigned r=(v>>11)&31u,g=(v>>5)&63u,b=v&31u;
    rgba[0]=(uint8_t)((r<<3)|(r>>2));
    rgba[1]=(uint8_t)((g<<2)|(g>>4));
    rgba[2]=(uint8_t)((b<<3)|(b>>2));
    rgba[3]=255;
}
/* Decode one compressed color block. BC1 3-color mode treats index 3 as
 * transparent; BC3 always uses 4-color interpolation, regardless of order. */
static void color_palette(const uint8_t *block,int bc3,
                          uint8_t colors[4][4]) {
    const uint16_t c0=little16(block),c1=little16(block+2);
    unpack565(c0,colors[0]);
    unpack565(c1,colors[1]);
    if (bc3||c0>c1) {
        for (unsigned k=0;k<3;++k) {
            colors[2][k]=(uint8_t)((2u*colors[0][k]+colors[1][k])/3u);
            colors[3][k]=(uint8_t)((colors[0][k]+2u*colors[1][k])/3u);
        }
        colors[2][3]=colors[3][3]=255;
    } else {
        for (unsigned k=0;k<3;++k)
            colors[2][k]=(uint8_t)((colors[0][k]+colors[1][k])/2u);
        colors[2][3]=255;
        memset(colors[3],0,4);
    }
}
static void alpha_palette(const uint8_t *block,uint8_t alphas[8]) {
    const unsigned a0=block[0],a1=block[1];
    alphas[0]=(uint8_t)a0; alphas[1]=(uint8_t)a1;
    if (a0>a1) {
        for(unsigned i=2;i<8;++i)
            alphas[i]=(uint8_t)(((8u-i)*a0+(i-1u)*a1)/7u);
    } else {
        for(unsigned i=2;i<6;++i)
            alphas[i]=(uint8_t)(((6u-i)*a0+(i-1u)*a1)/5u);
        alphas[6]=0; alphas[7]=255;
    }
}
static void decode_bcn(const uint8_t *src,uint8_t *dst,
                       uint32_t width,uint32_t height,int bc3) {
    const unsigned block_size=bc3?16u:8u;
    const uint32_t blocks_x=width/4u,blocks_y=height/4u;
    for (uint32_t by=0;by<blocks_y;++by) {
        for (uint32_t bx=0;bx<blocks_x;++bx) {
            const uint8_t *block=src+
                ((size_t)by*blocks_x+bx)*block_size;
            const uint8_t *color=block+(bc3?8u:0u);
            uint8_t rgba[4][4],alpha[8]={0};
            color_palette(color,bc3,rgba);
            uint64_t alpha_bits=0;
            if (bc3) {
                alpha_palette(block,alpha);
                for (unsigned i=0;i<6;++i)
                    alpha_bits|=((uint64_t)block[2+i])<<(8u*i);
            }
            const uint32_t indices=little32(color+4);
            for(unsigned j=0;j<16;++j) {
                const uint32_t x=bx*4u+(j%4u),y=by*4u+(j/4u);
                uint8_t *pixel=dst+((size_t)y*width+x)*4u;
                const unsigned ci=(indices>>(2u*j))&3u;
                memcpy(pixel,rgba[ci],4);
                if (bc3)pixel[3]=alpha[(alpha_bits>>(3u*j))&7u];
            }
        }
    }
}

int foj_atlas_dds_decode(const uint8_t *dds,size_t len,
                         uint8_t *out,size_t cap,FojAtlasRgba8Info *info) {
    if (!dds||!out||!info)return 0;
    if (len<FOJ_ATLAS_DDS_HEADER_BYTES||
        memcmp(dds,"DDS ",4)!=0||little32(dds+4)!=124 ||
        little32(dds+76)!=32 ||
        little32(dds+108)!=0x1000U ||
        little32(dds+112)!=0 || little32(dds+116)!=0 ||
        little32(dds+120)!=0 || little32(dds+124)!=0)
        return 0;

    const uint32_t width=little32(dds+16),height=little32(dds+12);
    if (width<8||width>FOJ_ATLAS_MAX_WIDTH||width%8||
        !height||height>FOJ_ATLAS_MAX_HEIGHT||
        little32(dds+24)!=0||little32(dds+28)>1)
        return 0;
    const size_t bytes=(size_t)width*(size_t)height*4u;
    if (cap<bytes)return 0;

    const uint32_t pixel_flags=little32(dds+80);
    const uint32_t fourcc=little32(dds+84);
    const int rgba8=pixel_flags==0x41u && fourcc==0;
    const int bc1=pixel_flags==0x4u && fourcc==FOJ_DDS_DXT1;
    const int bc3=pixel_flags==0x4u && fourcc==FOJ_DDS_DXT5;
    if (!rgba8&&!bc1&&!bc3)return 0;

    size_t file_bytes=bytes;
    if (rgba8) {
        if (little32(dds+8)!=0x100fU || little32(dds+88)!=32 ||
            little32(dds+92)!=0x000000ffU ||
            little32(dds+96)!=0x0000ff00U ||
            little32(dds+100)!=0x00ff0000U ||
            little32(dds+104)!=0xff000000U ||
            little32(dds+20)!=width*4u)
            return 0;
    } else {
        /* This deliberately rejects mips, DX10 extensions, BC2/BC4/BC5,
         * non-block-aligned heights, and unexpected DDS header metadata. */
        if (height%4u || little32(dds+8)!=0x81007U ||
            little32(dds+88)!=0 || little32(dds+92)!=0 ||
            little32(dds+96)!=0 || little32(dds+100)!=0 ||
            little32(dds+104)!=0)
            return 0;
        file_bytes=((size_t)width/4u)*((size_t)height/4u)*
                   (bc3?16u:8u);
        if (little32(dds+20)!=file_bytes)return 0;
    }
    if (len!=FOJ_ATLAS_DDS_HEADER_BYTES+file_bytes)return 0;

    if (rgba8)memcpy(out,dds+FOJ_ATLAS_DDS_HEADER_BYTES,bytes);
    else decode_bcn(dds+FOJ_ATLAS_DDS_HEADER_BYTES,out,width,height,bc3);
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
