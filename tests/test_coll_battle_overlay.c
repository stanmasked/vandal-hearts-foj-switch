/* Generated-only tests for the optional private COLL observation panel.
 * Values have no original gameplay meaning. */
#define _POSIX_C_SOURCE 200809L
#include "coll_battle_overlay.h"
#include "local_coll_window.h"

#include <assert.h>
#include <math.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

enum { W = 640, H = 360, STRIDE = 647 };
static FojCollBattleWindow window;

static void synthetic_window(void) {
    memset(&window, 0, sizeof(window));
    window.source_width = 50;
    window.source_height = 50;
    window.source_x = 21;
    window.source_y = 22;
    for (int y=0;y<FOJ_HEIGHT;++y) {
        for (int x=0;x<FOJ_WIDTH;++x) {
            window.raw[y][x][0] = (float)(x+y);
            window.raw[y][x][1] = (float)(x*6-y*2);
            window.raw[y][x][2] = -4.0f;
            window.raw[y][x][3] = (float)(x-y);
            window.flags[y][x][0] = (uint8_t)((x+y)%2);
            window.flags[y][x][1] = (uint8_t)((x+2*y)%3==0);
        }
    }
}

static void test_diagnostic_panel_is_read_only(void) {
    synthetic_window();
    FojCollBattleWindow old = window;
    uint32_t *pixels = malloc((size_t)STRIDE*H*sizeof(*pixels));
    assert(pixels);
    for (size_t i=0;i<(size_t)STRIDE*H;++i) pixels[i]=0x12345678u;
    assert(foj_coll_battle_overlay(&window,pixels,W,H,STRIDE,3,4,0));
    assert(memcmp(&window,&old,sizeof(old))==0);
    assert(pixels[(size_t)16*STRIDE+(size_t)430] != 0x12345678u);
    assert(pixels[(size_t)137*STRIDE+(size_t)505] ==
           UINT32_C(0xff78e2ff)); /* yellow selection frame */
    for (int y=0;y<H;++y)
        for (int x=W;x<STRIDE;++x)
            assert(pixels[(size_t)y*STRIDE+(size_t)x] == 0x12345678u);
    free(pixels);
}

static void test_each_raw_channel_can_be_drawn(void) {
    synthetic_window();
    uint32_t *pixels = calloc((size_t)W*H,sizeof(*pixels));
    assert(pixels);
    const int left=W-16-(FOJ_WIDTH*22+18);
    const int x=left+9+2*22+9, y=16+33+3*22+9;
    uint32_t colors[6];
    for (unsigned channel=0;channel<6;++channel) {
        assert(foj_coll_battle_overlay(&window,pixels,W,H,W,0,0,channel));
        colors[channel]=pixels[(size_t)y*W+(size_t)x];
    }
    assert(colors[0]!=colors[1]);
    assert(colors[2] != 0); /* constant numeric channel remains finite */
    assert(colors[4]!=colors[5]); /* separate boolean interpretations */
    assert(colors[4]==UINT32_C(0xff85b128)); /* flag true */
    assert(colors[5]==UINT32_C(0xff4d413d)); /* flag false */
    free(pixels);
}

static void test_invalid_input_does_not_touch_canvas(void) {
    synthetic_window();
    uint32_t *pixels=malloc((size_t)W*H*sizeof(*pixels));
    assert(pixels);
    for (size_t i=0;i<(size_t)W*H;++i) pixels[i]=UINT32_C(0xabcddcba);
    assert(!foj_coll_battle_overlay(NULL,pixels,W,H,W,0,0,0));
    assert(!foj_coll_battle_overlay(&window,NULL,W,H,W,0,0,0));
    assert(!foj_coll_battle_overlay(&window,pixels,200,H,W,0,0,0));
    assert(!foj_coll_battle_overlay(&window,pixels,W,180,W,0,0,0));
    assert(!foj_coll_battle_overlay(&window,pixels,W,H,W-1,0,0,0));
    assert(!foj_coll_battle_overlay(&window,pixels,W,H,W,-1,0,0));
    assert(!foj_coll_battle_overlay(&window,pixels,W,H,W,0,0,6));
    window.raw[0][0][1]=NAN;
    assert(!foj_coll_battle_overlay(&window,pixels,W,H,W,0,0,1));
    window.raw[0][0][1]=1;
    window.flags[1][0][0]=3;
    assert(!foj_coll_battle_overlay(&window,pixels,W,H,W,0,0,4));
    for (size_t i=0;i<(size_t)W*H;++i)
        assert(pixels[i]==UINT32_C(0xabcddcba));
    free(pixels);
}

static void write_generated_coll(FILE *file) {
    assert(fputs("8,6,0,0,1,1,\n",file)>=0);
    for (int y=0;y<FOJ_HEIGHT;++y)
        for (int x=0;x<FOJ_WIDTH;++x)
            assert(fprintf(file,"%d,%d,%d,%d,0,0,%s,%s,\n",
                           x,y,x,y,(x+y)%2?"true":"false",
                           x==y?"true":"false")>0);
}

static void test_shared_loader_rejects_bad_files_and_preserves_raw_bytes(void) {
    char pathname[]="/tmp/foj221-coll-XXXXXX";
    int fd=mkstemp(pathname);
    assert(fd>=0);
    FILE *file=fdopen(fd,"wb");
    assert(file);
    write_generated_coll(file);
    assert(fclose(file)==0);
    FojCollBattleWindow selected;
    assert(foj_local_coll_load_path(pathname,&selected));
    assert(selected.source_x==0 && selected.source_y==0);
    assert(selected.source_width==FOJ_WIDTH && selected.source_height==FOJ_HEIGHT);
    assert(selected.raw[3][5][0]==5.0f);
    assert(selected.raw[3][5][1]==3.0f);
    assert(selected.flags[3][5][0]==0);
    assert(selected.flags[3][3][1]==1);
    assert(!foj_local_coll_load_path(NULL,&selected));
    assert(selected.source_width==0);
    file=fopen(pathname,"wb");
    assert(file);
    assert(fputs("garbage\n",file)>0);
    assert(fclose(file)==0);
    assert(!foj_local_coll_load_path(pathname,&selected));
    assert(selected.source_width==0);
    assert(unlink(pathname)==0);
    assert(!foj_local_coll_load_path(pathname,&selected));
    assert(!foj_local_coll_load_path(pathname,NULL));
}

int main(void) {
    test_diagnostic_panel_is_read_only();
    test_each_raw_channel_can_be_drawn();
    test_invalid_input_does_not_touch_canvas();
    test_shared_loader_rejects_bad_files_and_preserves_raw_bytes();
    puts("Stage221 synthetic COLL panel: four test scenarios passed");
    return 0;
}
