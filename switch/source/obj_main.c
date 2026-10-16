/* FoJ Switch native geometry-only research.
 *
 * Reads a local user-provided first-shape OBJ from SD (if present);
 * otherwise displays an invented wireframe cube. This is not the FoJ
 * original renderer or a playable Switch game.
 */
#include <switch.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>

#include "obj_wireframe.h"

enum { FRAME_W=1280, FRAME_H=720 };

int main(int argc, char **argv) {
    (void)argc; (void)argv;

    FojObjMesh *mesh=malloc(sizeof(*mesh));
    if (!mesh) return 1;
    const char *path = "sdmc:/switch/foj/models/preview.obj";

    FILE *file=fopen(path,"rb");
    if (!file && R_SUCCEEDED(fsdevMountSdmc())) file=fopen(path,"rb");
    bool loaded = false;
    if (file) {
        loaded = foj_obj_read(file,mesh)==0;
        fclose(file);
    }
    if (!loaded) foj_obj_synthetic_cube(mesh);

    padConfigureInput(1,HidNpadStyleSet_NpadStandard);
    PadState pad;
    padInitializeDefault(&pad);

    Framebuffer fb;
    Result rc=framebufferCreate(&fb,nwindowGetDefault(),FRAME_W,FRAME_H,
                                PIXEL_FORMAT_RGBA_8888,2);
    if (R_FAILED(rc)) {free(mesh);return 2;}
    rc=framebufferMakeLinear(&fb);
    if (R_FAILED(rc)) {
        framebufferClose(&fb);
        free(mesh);
        return 3;
    }
    float yaw=0.5f,pitch=0.25f,zoom=1.0f;
    bool redraw=true;
    while (appletMainLoop()) {
        padUpdate(&pad);
        u64 buttons=padGetButtonsDown(&pad);
        if (buttons & HidNpadButton_Plus) break;
        if (buttons & HidNpadButton_Left) {yaw-=0.15f;redraw=true;}
        if (buttons & HidNpadButton_Right) {yaw+=0.15f;redraw=true;}
        if (buttons & HidNpadButton_Up) {pitch+=0.15f;redraw=true;}
        if (buttons & HidNpadButton_Down) {pitch-=0.15f;redraw=true;}
        if (buttons & HidNpadButton_ZR && zoom<4.f) {zoom*=1.25f;redraw=true;}
        if (buttons & HidNpadButton_ZL && zoom>.25f) {zoom/=1.25f;redraw=true;}
        if (pitch>1.5f) pitch=1.5f;
        if (pitch< -1.5f) pitch=-1.5f;

        u32 stride_bytes=0;
        u32 *pixels=(u32 *)framebufferBegin(&fb,&stride_bytes);
        if (pixels) {
            foj_obj_wireframe(mesh,(uint32_t *)pixels,FRAME_W,FRAME_H,
                              (int)(stride_bytes/sizeof(u32)),yaw,pitch,zoom);
            int stride=(int)(stride_bytes/sizeof(u32));
            /* Green: local OBJ loaded. Red: synthetic cube. */
            uint32_t marker=loaded ? UINT32_C(0xff60c376) :
                                     UINT32_C(0xff565ee7);
            for (int y=14;y<35;++y)
                for (int x=FRAME_W-48;x<FRAME_W-15;++x)
                    pixels[(size_t)y*(size_t)stride+x]=marker;
        }
        framebufferEnd(&fb);
        redraw=false;
        (void)redraw; /* Still redraw for double-buffer correctness. */
    }
    framebufferClose(&fb);
    free(mesh);
    return 0;
}
