/* Synthetic 8x8 DDS -> RGBA8 stdout bridge for cross-language test only.
 * The probe accepts bytes via stdin (no local filename or private art).
 * It emits NO pixel data until the native atlas parser fully accepts input.
 * Not a Switch runtime/GPU shader/scanout test. */
#include <stdio.h>
#include <stdint.h>
#include "atlas_dds.h"

enum { FIXTURE_BYTES=128+8*8*4, PIXEL_BYTES=8*8*4 };

int main(void) {
    uint8_t input[FIXTURE_BYTES+1u];
    uint8_t pixels[PIXEL_BYTES];
    FojAtlasRgba8Info info={0};
    const size_t length=fread(input,1,sizeof(input),stdin);
    if (ferror(stdin) || length!=FIXTURE_BYTES ||
        !foj_atlas_dds_decode(input,length,pixels,sizeof(pixels),&info) ||
        info.width!=8u || info.height!=8u ||
        info.pixel_bytes!=PIXEL_BYTES) {
        fputs("Invalid synthetic DDS pixel fixture\n",stderr);
        return 2;
    }
    if (fwrite(pixels,1,info.pixel_bytes,stdout)!=info.pixel_bytes ||
        fflush(stdout)!=0) {
        fputs("Unable to write native synthetic pixels\n",stderr);
        return 3;
    }
    return 0;
}
