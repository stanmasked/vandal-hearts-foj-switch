/* Stage273: decoded opaque-rear DDS contract, host C11 only. */
#include "alpha_material_contract.h"
#include <stdio.h>
#include <string.h>
static int count=0;
#define CHECK(test) do {++count;if(!(test)){ \
 fprintf(stderr,"Stage273 rear atlas guard FAIL line %d\n",__LINE__); \
 return 1; } } while(0)
int main(void){
    uint8_t rgba[8*8*4];
    memset(rgba,255,sizeof(rgba));
    FojAtlasRgba8Info info={8,8,sizeof(rgba)};
    CHECK(foj_gpu_opaque_rear_atlas(rgba,&info)==1);
    rgba[7]=254;
    CHECK(foj_gpu_opaque_rear_atlas(rgba,&info)==0);
    rgba[7]=0;
    CHECK(foj_gpu_opaque_rear_atlas(rgba,&info)==0);
    rgba[7]=255;
    CHECK(foj_gpu_opaque_rear_atlas(rgba,&info)==1);
    CHECK(foj_gpu_opaque_rear_atlas(NULL,&info)==0);
    CHECK(foj_gpu_opaque_rear_atlas(rgba,NULL)==0);
    info.pixel_bytes--;
    CHECK(foj_gpu_opaque_rear_atlas(rgba,&info)==0);
    info.pixel_bytes=sizeof(rgba);
    info.width=0;
    CHECK(foj_gpu_opaque_rear_atlas(rgba,&info)==0);
    info.width=7;
    CHECK(foj_gpu_opaque_rear_atlas(rgba,&info)==0);
    info.width=257;
    CHECK(foj_gpu_opaque_rear_atlas(rgba,&info)==0);
    info.width=8;
    info.height=0;
    CHECK(foj_gpu_opaque_rear_atlas(rgba,&info)==0);
    info.height=257;
    CHECK(foj_gpu_opaque_rear_atlas(rgba,&info)==0);
    info.height=8;
    CHECK(foj_gpu_opaque_rear_atlas(rgba,&info)==1);
    printf("Stage273 opaque rear DDS: %d cases pass\n",count);
    return 0;
}
