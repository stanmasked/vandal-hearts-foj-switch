#include "research_texture.h"

int foj_research_texture_rgba8(unsigned material,
                               uint8_t* out,size_t capacity) {
    if (!out || capacity<FOJ_RESEARCH_TEXTURE_BYTES ||
        material>=FOJ_RESEARCH_TEXTURE_COUNT)
        return 0;
    for (unsigned y=0;y<FOJ_RESEARCH_TEXTURE_HEIGHT;++y) {
        for (unsigned x=0;x<FOJ_RESEARCH_TEXTURE_WIDTH;++x) {
            size_t offset=(y*FOJ_RESEARCH_TEXTURE_WIDTH+x)*4u;
            /* Different high-contrast gradients make per-batch image
             * selection recognizable without relying on PS3 artwork. */
            out[offset+0]=(uint8_t)(material==0? 192+4*x:32+4*y);
            out[offset+1]=(uint8_t)(material==0? 32+4*y:92+4*x);
            out[offset+2]=(uint8_t)(material==0? 42+2*y:188+4*x);
            out[offset+3]=255;
        }
    }
    return 1;
}
