#include "alpha_material_contract.h"
#include <stddef.h>

/* Strictly bounded and fail-closed. The existing atlas DDS intake already
 * decodes to canonical RGBA8. We additionally enforce the only opaque
 * material's alpha, because dynamic depth writes assume it is 255.
 */
int foj_gpu_opaque_rear_atlas(
    const uint8_t *pixels, const FojAtlasRgba8Info *info) {
    if(!pixels||!info||
       info->width<8u || info->width>FOJ_ATLAS_MAX_WIDTH ||
       info->height<1u || info->height>FOJ_ATLAS_MAX_HEIGHT)
        return 0;
    const size_t count=(size_t)info->width*info->height;
    if(count>FOJ_ATLAS_MAX_BYTES/4u||
       info->pixel_bytes!=count*4u)return 0;
    for(size_t i=0;i<count;++i) {
        if(pixels[4u*i+3u]!=UINT8_MAX)return 0;
    }
    return 1;
}
