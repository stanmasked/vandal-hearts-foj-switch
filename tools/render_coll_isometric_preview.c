/* Host-only visual reference for the exact portable COLL isometric plot.
 * Every input cell is invented; NOT a PS3 asset or console screenshot. */
#include "coll_grid.h"
#include "coll_iso_view.h"
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>

enum { WIDTH=1280, HEIGHT=720 };
static FojCollGrid generated;

int main(int argc,char **argv) {
    if (argc!=2) {
        fputs("Usage: foj-coll-isometric-preview OUTPUT.ppm\n",stderr);
        return 2;
    }
    generated.width=50;
    generated.height=50;
    generated.origin[0]=generated.origin[1]=-250.0f;
    generated.step[0]=generated.step[1]=10.0f;
    for (int y=0;y<50;++y)
        for (int x=0;x<50;++x) {
            for (int ch=0;ch<4;++ch)
                generated.samples[y][x][ch]=
                    (float)((x*3+y*5+ch*7)%70)-19.0f;
            generated.flags[y][x][0]=(uint8_t)((x+y)%11==0);
            generated.flags[y][x][1]=(uint8_t)((x*3+y)%31==0);
        }

    uint32_t *pixels=calloc((size_t)WIDTH*(size_t)HEIGHT,sizeof(*pixels));
    if (!pixels)return 3;
    foj_coll_iso_render(&generated,pixels,WIDTH,HEIGHT,WIDTH,25,25,14,0);
    FILE *output=fopen(argv[1],"wb");
    if (!output) {
        free(pixels);
        fputs("Unable to create generated reference\n",stderr);
        return 4;
    }
    int ok=fprintf(output,"P6\n%d %d\n255\n",WIDTH,HEIGHT)>0;
    const size_t count=(size_t)WIDTH*(size_t)HEIGHT;
    for (size_t i=0;i<count && ok;++i) {
        const uint32_t v=pixels[i];
        const unsigned char rgb[3]={
            (unsigned char)(v&255u),
            (unsigned char)((v>>8u)&255u),
            (unsigned char)((v>>16u)&255u)
        };
        ok=fwrite(rgb,1,sizeof(rgb),output)==sizeof(rgb);
    }
    if (fclose(output)!=0)ok=0;
    free(pixels);
    return ok?0:5;
}
