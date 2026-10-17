#ifndef FOJ_RESEARCH_TEXTURE_H
#define FOJ_RESEARCH_TEXTURE_H
/* Two deterministic, synthetic RGBA8 texels sources. Research only.
 * Images and material indices do not contain any FoJ game assets. */
#include <stddef.h>
#include <stdint.h>
enum {
    FOJ_RESEARCH_TEXTURE_COUNT=2,
    FOJ_RESEARCH_TEXTURE_WIDTH=8,
    FOJ_RESEARCH_TEXTURE_HEIGHT=8,
    FOJ_RESEARCH_TEXTURE_BYTES=8*8*4
};
/* Transactional: on failure, does not modify the destination buffer. */
int foj_research_texture_rgba8(unsigned material,
                               uint8_t* out,size_t capacity);
#endif
