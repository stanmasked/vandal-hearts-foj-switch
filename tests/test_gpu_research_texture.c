/* Two independent synthetic RGBA8 textures; portable host-only test. */
#ifdef NDEBUG
#undef NDEBUG
#endif
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include "research_texture.h"

int main(void) {
    uint8_t a[FOJ_RESEARCH_TEXTURE_BYTES];
    uint8_t b[FOJ_RESEARCH_TEXTURE_BYTES];
    memset(a,0xA5,sizeof(a));
    assert(!foj_research_texture_rgba8(2,a,sizeof(a)));
    assert(!foj_research_texture_rgba8(0,a,sizeof(a)-1));
    assert(!foj_research_texture_rgba8(0,NULL,sizeof(a)));
    for (size_t i=0;i<sizeof(a);++i)assert(a[i]==0xA5);

    assert(foj_research_texture_rgba8(0,a,sizeof(a)));
    assert(foj_research_texture_rgba8(1,b,sizeof(b)));
    assert(memcmp(a,b,sizeof(a))!=0);
    for (size_t i=0;i<sizeof(a);i+=4) {
        assert(a[i+3]==255 && b[i+3]==255);
        assert(a[i]>a[i+2]);
        assert(b[i+2]>b[i]);
    }
    uint8_t repeat[FOJ_RESEARCH_TEXTURE_BYTES];
    assert(foj_research_texture_rgba8(0,repeat,sizeof(repeat)));
    assert(memcmp(a,repeat,sizeof(a))==0);
    puts("GPU synthetic two-material RGBA8 textures: PASS");
    return 0;
}
