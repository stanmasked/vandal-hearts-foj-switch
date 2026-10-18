/* Generated-only COLL isometric data plot: no game maps are committed. */
#ifdef NDEBUG
#undef NDEBUG
#endif
#include "coll_grid.h"
#include "coll_iso_view.h"
#include "coll_view.h"
#include <assert.h>
#include <math.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static FojCollGrid *synthetic(unsigned width,unsigned height) {
    FojCollGrid *grid=calloc(1,sizeof(*grid));
    assert(grid);
    grid->width=(int)width;
    grid->height=(int)height;
    grid->step[0]=grid->step[1]=10.0f;
    for (unsigned y=0;y<height;++y)
        for (unsigned x=0;x<width;++x) {
            grid->samples[y][x][0]=(float)x*2.0f-(float)y;
            grid->samples[y][x][1]=(float)x+(float)y*3.0f;
            grid->samples[y][x][2]=8.0f; /* constant: no extrusion */
            grid->samples[y][x][3]=-(float)x;
            grid->flags[y][x][0]=(uint8_t)((x+y)%3u==0u);
            grid->flags[y][x][1]=(uint8_t)((x+y)%5u==0u);
        }
    return grid;
}
static uint64_t fingerprint(const uint32_t *pixels,size_t count) {
    uint64_t h=UINT64_C(1469598103934665603);
    for (size_t i=0;i<count;++i) {
        h^=(uint64_t)pixels[i];
        h*=UINT64_C(1099511628211);
    }
    return h;
}

static void test_all_six_channels_and_cursor(void) {
    enum { W=240,H=160,S=256 };
    uint32_t *pixels=malloc(sizeof(uint32_t)*H*S);
    FojCollGrid *grid=synthetic(50,50);
    assert(pixels);
    uint64_t hashes[6]={0};
    for (int channel=0;channel<6;++channel) {
        for (size_t i=0;i<(size_t)H*S;++i)
            pixels[i]=UINT32_C(0x12345678);
        foj_coll_iso_render(grid,pixels,W,H,S,24,24,12,channel);
        hashes[channel]=fingerprint(pixels,(size_t)H*S);
        for (int y=0;y<H;++y)
            for (int x=W;x<S;++x)
                assert(pixels[(size_t)y*S+x]==UINT32_C(0x12345678));
        /* Cursor is drawn as a yellow outline above all cells. */
        uint32_t gold=UINT32_C(0xff76e0ff);
        int at=H/2-12/2;
        if (channel<4 && channel!=2) {
            /* Numeric extrusion can move the outline up by 0..32. */
            int found=0;
            for (int y=at-32;y<=at;++y)
                if (pixels[(size_t)y*S+W/2]==gold)found=1;
            assert(found);
        } else {
            assert(pixels[(size_t)at*S+W/2]==gold);
        }
    }
    assert(hashes[0]!=hashes[1]);
    assert(hashes[0]!=hashes[3]);
    assert(hashes[2]!=hashes[4]);
    assert(hashes[4]!=hashes[5]);
    free(pixels);
    free(grid);
}

static void test_flag_colors_and_numeric_constant(void) {
    enum { W=120,H=96 };
    uint32_t pixels[W*H];
    FojCollGrid *grid=synthetic(2,2);
    assert(grid);
    foj_coll_iso_render(grid,pixels,W,H,W,0,0,16,4);
    /* Flag 0 in first cell is true; flag 1 also true at origin. */
    assert(pixels[(H/2)*W+W/2]==UINT32_C(0xff7061d9));
    foj_coll_iso_render(grid,pixels,W,H,W,1,0,16,4);
    /* Cell (1,0) false in flag 0. Cursor moves with centered camera. */
    assert(pixels[(H/2)*W+W/2]==UINT32_C(0xff675935));
    foj_coll_iso_render(grid,pixels,W,H,W,0,0,16,2);
    /* Constant column cannot imply terrain elevation. */
    assert(pixels[(H/2-8)*W+W/2]==UINT32_C(0xff76e0ff));
    free(grid);
}

static void test_invalid_arguments_and_untrusted_values_preserve_bytes(void) {
    enum { W=64,H=48 };
    uint32_t frame[W*H];
    FojCollGrid *grid=synthetic(3,3);
    assert(grid);
    for (unsigned scenario=0;scenario<12u;++scenario) {
        for (size_t i=0;i<(size_t)W*H;++i)
            frame[i]=UINT32_C(0x12345678);
        switch (scenario) {
            case 0: foj_coll_iso_render(NULL,frame,W,H,W,1,1,12,0);break;
            case 1: foj_coll_iso_render(grid,NULL,W,H,W,1,1,12,0);break;
            case 2: foj_coll_iso_render(grid,frame,0,H,W,1,1,12,0);break;
            case 3: foj_coll_iso_render(grid,frame,W,H,W-1,1,1,12,0);break;
            case 4: foj_coll_iso_render(grid,frame,W,H,W,-1,1,12,0);break;
            case 5: foj_coll_iso_render(grid,frame,W,H,W,1,3,12,0);break;
            case 6: foj_coll_iso_render(grid,frame,W,H,W,1,1,2,0);break;
            case 7: foj_coll_iso_render(grid,frame,W,H,W,1,1,31,0);break;
            case 8: foj_coll_iso_render(grid,frame,W,H,W,1,1,12,-1);break;
            case 9: foj_coll_iso_render(grid,frame,W,H,W,1,1,12,6);break;
            case 10:
                grid->samples[1][1][0]=NAN;
                foj_coll_iso_render(grid,frame,W,H,W,1,1,12,0);
                grid->samples[1][1][0]=0.0f;
                break;
            case 11:
                grid->flags[1][1][0]=2;
                foj_coll_iso_render(grid,frame,W,H,W,1,1,12,4);
                grid->flags[1][1][0]=0;
                break;
        }
        for (size_t i=0;i<(size_t)W*H;++i)
            assert(frame[i]==UINT32_C(0x12345678));
    }
    free(grid);
}

static void test_extreme_finite_float_range_and_clipping(void) {
    enum { W=48,H=32,S=52 };
    uint32_t frame[H*S];
    FojCollGrid *grid=synthetic(2,2);
    assert(grid);
    grid->samples[0][0][0]=-3.4e38f;
    grid->samples[0][1][0]=3.4e38f;
    for (size_t i=0;i<(size_t)H*S;++i) frame[i]=UINT32_C(0xdeadbeef);
    foj_coll_iso_render(grid,frame,W,H,S,0,0,30,0);
    assert(frame[0]==UINT32_C(0xff231610));
    for (int y=0;y<H;++y)
        for (int x=W;x<S;++x)
            assert(frame[(size_t)y*S+x]==UINT32_C(0xdeadbeef));
    free(grid);
}

int main(void) {
    test_all_six_channels_and_cursor();
    test_flag_colors_and_numeric_constant();
    test_invalid_arguments_and_untrusted_values_preserve_bytes();
    test_extreme_finite_float_range_and_clipping();
    puts("COLL isometric raw-channel diagnostic: four generated tests passed");
    return 0;
}
