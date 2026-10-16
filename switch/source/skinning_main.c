/*
 * FoJ native CPU skinning mechanics demonstrator.
 *
 * This application renders ONLY an INVENTED 2-bone hinged strip. It uses
 * the same portable skeletal_skin.c functions that can eventually animate
 * user-provided FoJ meshes. It is NOT original-game graphics, original
 * PS3 animation playback, or a playable port.
 */
#include <switch.h>
#include <math.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>

#include "skeletal_skin.h"
#include "obj_wireframe.h"

enum { VIEW_W=1280, VIEW_H=720, N_VERTICES=8, N_FACES=4 };

static void make_synthetic_figure(FojObjMesh *mesh,
                                  FojSkinnedVertex vertices[N_VERTICES]) {
    memset(mesh, 0, sizeof(*mesh));
    memset(vertices, 0, N_VERTICES*sizeof(*vertices));
    static const float points[N_VERTICES][3] = {
        {-.25f,0.f,0.f}, {.25f,0.f,0.f},
        {.25f,1.2f,0.f}, {-.25f,1.2f,0.f},
        {-.25f,1.2f,0.f}, {.25f,1.2f,0.f},
        {.25f,2.4f,0.f}, {-.25f,2.4f,0.f}
    };
    static const FojTri faces[N_FACES] = {
        {0,1,2}, {0,2,3}, {4,5,6}, {4,6,7}
    };
    mesh->vertex_count=N_VERTICES;
    mesh->triangle_count=N_FACES;
    memcpy(mesh->faces, faces, sizeof(faces));
    mesh->center[0]=0.f;
    mesh->center[1]=1.15f;
    mesh->center[2]=0.f;
    mesh->radius=3.f;
    for (unsigned i=0;i<N_VERTICES;++i) {
        for (int j=0;j<3;++j) vertices[i].xyz[j]=points[i][j];
        vertices[i].influence_count=1;
        vertices[i].influences[0].bone=(uint16_t)(i<4?0:1);
        vertices[i].influences[0].weight=1.f;
    }
}

static int update_geometry(FojObjMesh *mesh,
                           const FojSkinnedVertex input[N_VERTICES],
                           float seconds) {
    FojBoneTransform bind[2]={0}, pose[2]={0};
    bind[0].parent=-1;
    bind[0].rotation_xyzw[3]=1.f;
    bind[1].parent=0;
    bind[1].rotation_xyzw[3]=1.f;
    bind[1].translation_xyz[1]=1.2f;
    memcpy(pose, bind, sizeof(bind));

    /* Clearly synthetic, exaggerated oscillation of the upper arm.
       The real FoJ bind/animation coordinate conventions are not proven. */
    float angle=.95f*sinf(seconds*1.6f);
    pose[1].rotation_xyzw[2]=sinf(angle*.5f);
    pose[1].rotation_xyzw[3]=cosf(angle*.5f);

    FojSkinMatrix palette[2];
    float output[N_VERTICES*3];
    if (foj_skin_build_palette(bind,pose,2,palette,2)!=FOJ_SKIN_OK)
        return 0;
    if (foj_skin_deform(input,N_VERTICES,palette,2,output,
                        N_VERTICES*3)!=FOJ_SKIN_OK)
        return 0;
    for (unsigned i=0;i<N_VERTICES;++i) {
        mesh->vertices[i].x=output[3*i];
        mesh->vertices[i].y=output[3*i+1];
        mesh->vertices[i].z=output[3*i+2];
    }
    return 1;
}

int main(int argc, char **argv) {
    (void)argc;(void)argv;
    FojObjMesh *mesh=malloc(sizeof(*mesh));
    if (!mesh) return 1;
    FojSkinnedVertex source[N_VERTICES];
    make_synthetic_figure(mesh,source);
    if (!update_geometry(mesh,source,0)) {free(mesh);return 2;}

    padConfigureInput(1,HidNpadStyleSet_NpadStandard);
    PadState pad;
    padInitializeDefault(&pad);

    Framebuffer fb;
    Result result=framebufferCreate(&fb,nwindowGetDefault(),
                                    VIEW_W,VIEW_H,PIXEL_FORMAT_RGBA_8888,2);
    if (R_FAILED(result)) {free(mesh);return 3;}
    result=framebufferMakeLinear(&fb);
    if (R_FAILED(result)) {
        framebufferClose(&fb);free(mesh);return 4;
    }

    float yaw=.3f,pitch=.15f,zoom=1.f,time=0;
    int playing=1;
    while (appletMainLoop()) {
        padUpdate(&pad);
        u64 keys=padGetButtonsDown(&pad);
        if (keys&HidNpadButton_Plus)break;
        if (keys&HidNpadButton_A)playing=!playing;
        if (keys&HidNpadButton_B){playing=0;time=0;}
        if (keys&HidNpadButton_Left)yaw-=.12f;
        if (keys&HidNpadButton_Right)yaw+=.12f;
        if (keys&HidNpadButton_Up)pitch+=.12f;
        if (keys&HidNpadButton_Down)pitch-=.12f;
        if (keys&HidNpadButton_ZR && zoom<4.f)zoom*=1.25f;
        if (keys&HidNpadButton_ZL && zoom>.25f)zoom/=1.25f;
        if (pitch>1.5f)pitch=1.5f;
        if (pitch< -1.5f)pitch=-1.5f;

        if (playing)time+=1.f/60.f;
        if (!update_geometry(mesh,source,time))break;

        u32 stride_bytes=0;
        u32 *pixels=(u32*)framebufferBegin(&fb,&stride_bytes);
        if (pixels) {
            int stride=(int)(stride_bytes/sizeof(u32));
            foj_obj_wireframe(mesh,(uint32_t*)pixels,VIEW_W,VIEW_H,
                              stride,yaw,pitch,zoom);
            /* Red marker = always synthetic / no original game bytes. */
            for (int y=14;y<35;++y)
                for (int x=VIEW_W-48;x<VIEW_W-15;++x)
                    pixels[(size_t)y*(size_t)stride+x]=UINT32_C(0xff565ee7);
        }
        framebufferEnd(&fb);
    }
    framebufferClose(&fb);
    free(mesh);
    return 0;
}
