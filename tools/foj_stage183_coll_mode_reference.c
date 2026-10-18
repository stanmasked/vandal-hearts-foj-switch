/* Independently generate the exact synthetic COLL fallback through both
 * portable renderers used by the Switch research NRO. No original PS3 assets. */
#include "coll_grid.h"
#include "coll_view.h"
#include "coll_iso_view.h"
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

enum { FB_WIDTH=1280, FB_HEIGHT=720 };
static FojCollGrid map;

static void make_synthetic_map(void) {
    map.width=map.height=50;
    map.origin[0]=map.origin[1]=-250.0f;
    map.step[0]=map.step[1]=10.0f;
    for (int y=0;y<50;++y) for (int x=0;x<50;++x) {
        for (int sample=0;sample<4;++sample)
            map.samples[y][x][sample]=
                (float)((x*3+y*5+sample*9)%70)*0.4f-8.0f;
        map.flags[y][x][0]=(uint8_t)(((x+y)%11)==0);
        map.flags[y][x][1]=(uint8_t)(((x*3+y)%31)==0);
    }
}
static void fallback_status(uint32_t *frame) {
    const uint32_t color=UINT32_C(0xff565ee7);
    for (int y=16;y<35;++y)
        for (int x=FB_WIDTH-45;x<FB_WIDTH-18;++x)
            frame[(size_t)y*FB_WIDTH+(size_t)x]=color;
}
static int write_ppm(const char *path,const uint32_t *pixels) {
    FILE *file=fopen(path,"wb");
    if (!file)return 0;
    int okay=fprintf(file,"P6\n%d %d\n255\n",FB_WIDTH,FB_HEIGHT)>0;
    const size_t count=(size_t)FB_WIDTH*FB_HEIGHT;
    for (size_t i=0;i<count&&okay;++i) {
        const uint32_t rgba=pixels[i];
        const unsigned char rgb[3]={
            (unsigned char)(rgba&255u),
            (unsigned char)((rgba>>8u)&255u),
            (unsigned char)((rgba>>16u)&255u)
        };
        okay=fwrite(rgb,1,sizeof(rgb),file)==sizeof(rgb);
    }
    if (fclose(file)!=0)okay=0;
    return okay;
}
int main(int argc,char **argv) {
    if ((argc!=3&&argc!=7)||
        (strcmp(argv[1],"heatmap")!=0&&
         strcmp(argv[1],"isometric")!=0)) {
        fputs("Usage: coll-mode-reference heatmap|isometric OUTPUT.ppm [x y tile channel]\n",stderr);
        return 2;
    }
    int cx=25,cy=25,tile=12,channel=0;
    if (argc==7) {
        char extra=0;
        if (sscanf(argv[3],"%d%c",&cx,&extra)!=1||
            sscanf(argv[4],"%d%c",&cy,&extra)!=1||
            sscanf(argv[5],"%d%c",&tile,&extra)!=1||
            sscanf(argv[6],"%d%c",&channel,&extra)!=1||
            cx<0||cx>=50||cy<0||cy>=50||
            tile<4||tile>30||channel<0||channel>5)return 2;
    }
    make_synthetic_map();
    uint32_t *pixels=calloc((size_t)FB_WIDTH*FB_HEIGHT,sizeof(uint32_t));
    if (!pixels)return 3;
    if (strcmp(argv[1],"heatmap")==0)
        foj_coll_render(&map,pixels,FB_WIDTH,FB_HEIGHT,FB_WIDTH,
                        cx,cy,tile,channel);
    else
        foj_coll_iso_render(&map,pixels,FB_WIDTH,FB_HEIGHT,FB_WIDTH,
                            cx,cy,tile,channel);
    fallback_status(pixels);
    const int result=write_ppm(argv[2],pixels)?0:4;
    free(pixels);
    return result;
}
