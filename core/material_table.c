#include "material_table.h"
#include <string.h>

static uint32_t read32le(const uint8_t *p) {
    return (uint32_t)p[0] | ((uint32_t)p[1]<<8) |
           ((uint32_t)p[2]<<16) | ((uint32_t)p[3]<<24);
}

int foj_material_table_parse(const uint8_t *data,size_t length,
                             FojMaterialTable *out) {
    if (!data || !out || length<20 || memcmp(data,"FOJMAT01",8)!=0)
        return 1;
    size_t sections=read32le(data+8),textures=read32le(data+12);
    if (!sections || sections>FOJ_MAT_MAX_SECTIONS ||
        !textures || textures>FOJ_MAT_MAX_TEXTURES ||
        length!=16+sections*4) return 2;
    FojMaterialTable result={0};
    result.section_count=sections;
    result.texture_count=textures;
    unsigned char used[FOJ_MAT_MAX_TEXTURES]={0};
    for (size_t i=0;i<sections;++i) {
        uint32_t index=read32le(data+16+4*i);
        if (index>=textures)return 3;
        result.section_texture[i]=index;
        used[index]=1;
    }
    for (size_t i=0;i<textures;++i)
        if (!used[i])return 4;
    *out=result;
    return 0;
}
