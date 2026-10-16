#include "material_table.h"
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

static void le32(uint8_t *p,unsigned n) {
    for(int i=0;i<4;++i)p[i]=(uint8_t)(n>>(8*i));
}
static void test_table(void) {
    uint8_t bytes[32]={0};
    memcpy(bytes,"FOJMAT01",8);
    le32(bytes+8,3);le32(bytes+12,2);
    le32(bytes+16,1);le32(bytes+20,0);le32(bytes+24,1);
    FojMaterialTable t={0};
    assert(foj_material_table_parse(bytes,28,&t)==0);
    assert(t.section_count==3&&t.texture_count==2);
    assert(t.section_texture[0]==1&&t.section_texture[1]==0);
    assert(foj_material_table_parse(bytes,27,&t)!=0);
    le32(bytes+24,2);
    assert(foj_material_table_parse(bytes,28,&t)!=0);
    le32(bytes+24,1);
    le32(bytes+12,3);
    assert(foj_material_table_parse(bytes,28,&t)!=0);
    le32(bytes+12,2);
    le32(bytes+8,100);
    assert(foj_material_table_parse(bytes,28,&t)!=0);
    le32(bytes+8,3);
    bytes[0]=0;
    assert(foj_material_table_parse(bytes,28,&t)!=0);
}
int main(void){test_table();puts("FOJMAT01 material section parser passed");return 0;}
