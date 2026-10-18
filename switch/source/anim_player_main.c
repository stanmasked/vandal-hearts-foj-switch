/*
 * Stage 193: generated-only, animated two-bone Switch research NRO.
 * Uses the production portable-C animation controller and skinning palette.
 * No game assets, recovered PS3 scheduler or original gameplay.
 */
#include <switch.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>

#include "anim_player.h"
#include "obj_wireframe.h"

enum { WIDTH=1280, HEIGHT=720, VERTS=8, FACES=4 };

static void set_key(FojAnimKey *key, float t, float qz, float qw,
                    float x, float y) {
    memset(key,0,sizeof(*key));
    key->time=t;
    key->quat_xyzw[2]=qz;
    key->quat_xyzw[3]=qw;
    key->translation_xyz[0]=x;
    key->translation_xyz[1]=y;
}

static void make_clips(FojAnimClip clips[2], FojAnimTrack tracks[2][2],
                       FojAnimKey keys[2][2][2],
                       FojBoneTransform bind[2]) {
    memset(bind,0,2*sizeof(*bind));
    bind[0].parent=-1;
    bind[0].rotation_xyzw[3]=1.f;
    bind[1].parent=0;
    bind[1].rotation_xyzw[3]=1.f;
    bind[1].translation_xyz[1]=1.f;

    /* Invented clip A: gentle turn; clip B: opposite turn. All rotations
     * use local normalized XYZW quaternions; child parent index is 0. */
    set_key(&keys[0][0][0],0.f,0.f,1.f,0.f,0.f);
    set_key(&keys[0][0][1],1.f,.1305262f,.9914449f,.3f,0.f);
    set_key(&keys[0][1][0],0.f,0.f,1.f,0.f,1.f);
    set_key(&keys[0][1][1],1.f,.38268343f,.92387953f,0.f,1.f);
    set_key(&keys[1][0][0],0.f,-.38268343f,.92387953f,-.35f,0.f);
    set_key(&keys[1][0][1],1.f,-.5f,.8660254f,-.6f,0.f);
    set_key(&keys[1][1][0],0.f,-.5f,.8660254f,0.f,1.f);
    set_key(&keys[1][1][1],1.f,.38268343f,.92387953f,0.f,1.f);
    for (size_t clip=0;clip<2;++clip) {
        tracks[clip][0]=(FojAnimTrack){-1,2,keys[clip][0]};
        tracks[clip][1]=(FojAnimTrack){0,2,keys[clip][1]};
        clips[clip]=(FojAnimClip){1.f,2,tracks[clip]};
    }
}

static void make_strip(FojObjMesh *mesh,FojSkinnedVertex verts[VERTS]) {
    static const float points[VERTS][3]={
        {-.26f,0.f,0.f},{.26f,0.f,0.f},
        {.26f,1.f,0.f},{-.26f,1.f,0.f},
        {-.26f,1.f,0.f},{.26f,1.f,0.f},
        {.26f,2.f,0.f},{-.26f,2.f,0.f}
    };
    static const FojTri tris[FACES]={
        {0,1,2},{0,2,3},{4,5,6},{4,6,7}
    };
    memset(mesh,0,sizeof(*mesh));
    memset(verts,0,VERTS*sizeof(*verts));
    mesh->vertex_count=VERTS;
    mesh->triangle_count=FACES;
    mesh->center[1]=1.f;
    mesh->radius=2.75f;
    memcpy(mesh->faces,tris,sizeof(tris));
    for (size_t i=0;i<VERTS;++i) {
        for (int axis=0;axis<3;++axis)verts[i].xyz[axis]=points[i][axis];
        verts[i].influence_count=1;
        verts[i].influences[0]=(FojSkinInfluence){(uint16_t)(i<4?0:1),1.f};
    }
}

static int pose_vertices(FojObjMesh *mesh,
                         const FojSkinnedVertex verts[VERTS],
                         const FojBoneTransform bind[2],
                         const FojAnimPlayer *player) {
    FojSkinMatrix palette[2];
    float xyz[VERTS*3];
    if (foj_player_palette(player,bind,2,palette,2)!=FOJ_PLAYER_OK ||
        foj_skin_deform(verts,VERTS,palette,2,xyz,VERTS*3)!=FOJ_SKIN_OK)
        return 0;
    for (size_t i=0;i<VERTS;++i)
        mesh->vertices[i]=(FojVec3){xyz[i*3],xyz[i*3+1],xyz[i*3+2]};
    return 1;
}

static void rectangle(uint32_t *p, int stride, int x, int y, int w, int h,
                      uint32_t color) {
    for (int row=y;row<y+h;++row)
        for (int col=x;col<x+w;++col)
            p[(size_t)row*(size_t)stride+(size_t)col]=color;
}

static void draw_status(uint32_t *p,int stride,const FojAnimPlayer *player,
                        const FojAnimClip *a) {
    /* Unambiguous pixels independent of clock speed or emulator UI.
     * ABGR little-endian framebuffer; distinct markers are synthetic only.
     * HUD-safe red=synthetic, cyan=A, orange=B, green=paused, magenta=playing,
     * yellow=transition plus four incremental fade progress bars. */
    const uint32_t red=UINT32_C(0xff0000ff);
    const uint32_t cyan=UINT32_C(0xffffff00);
    const uint32_t orange=UINT32_C(0xff00a5ff);
    const uint32_t green=UINT32_C(0xff00ff00);
    const uint32_t magenta=UINT32_C(0xffff00ff);
    const uint32_t yellow=UINT32_C(0xff00ffff);
    rectangle(p,stride,300,24,52,52,red);
    rectangle(p,stride,1100,24,52,52,player->active==a?cyan:orange);
    rectangle(p,stride,1200,24,52,52,player->paused?green:magenta);
    if (player->incoming) {
        rectangle(p,stride,1000,24,52,52,yellow);
        const float alpha=player->fade_elapsed/player->fade_duration;
        for (int i=0;i<4;++i)
            if (alpha>=.24f+.25f*i)
                rectangle(p,stride,390+60*i,36,40,30,yellow);
    }
}

int main(int argc,char **argv) {
    (void)argc;(void)argv;
    FojBoneTransform bind[2];
    FojAnimKey keys[2][2][2];
    FojAnimTrack tracks[2][2];
    FojAnimClip clips[2];
    make_clips(clips,tracks,keys,bind);
    FojAnimPlayer player={0};
    if (foj_player_init(&player,&clips[0],bind,2)!=FOJ_PLAYER_OK ||
        foj_player_pause(&player,1)!=FOJ_PLAYER_OK)return 1;

    FojObjMesh *mesh=malloc(sizeof(*mesh));
    if (!mesh)return 2;
    FojSkinnedVertex vertices[VERTS];
    make_strip(mesh,vertices);

    padConfigureInput(1,HidNpadStyleSet_NpadStandard);
    PadState pad;padInitializeDefault(&pad);
    Framebuffer fb;
    Result rc=framebufferCreate(&fb,nwindowGetDefault(),WIDTH,HEIGHT,
                                PIXEL_FORMAT_RGBA_8888,2);
    if (R_FAILED(rc)){free(mesh);return 3;}
    rc=framebufferMakeLinear(&fb);
    if (R_FAILED(rc)){framebufferClose(&fb);free(mesh);return 4;}

    int failed=0;
    while (appletMainLoop()) {
        padUpdate(&pad);
        u64 buttons=padGetButtonsDown(&pad);
        if (buttons&HidNpadButton_Plus)break;
        if (buttons&HidNpadButton_B) {
            if (foj_player_init(&player,&clips[0],bind,2)!=FOJ_PLAYER_OK ||
                foj_player_pause(&player,1)!=FOJ_PLAYER_OK){failed=1;break;}
        }
        if (buttons&HidNpadButton_A) {
            if (foj_player_pause(&player,!player.paused)!=FOJ_PLAYER_OK)
                {failed=1;break;}
        }
        if (buttons&HidNpadButton_Y) {
            const FojAnimClip *target=player.active==&clips[0]
                                    ?&clips[1]:&clips[0];
            if (!player.incoming &&
                foj_player_switch(&player,target,bind,2,.5f)!=FOJ_PLAYER_OK)
                {failed=1;break;}
        }
        if ((buttons&HidNpadButton_Right) && player.paused) {
            if (foj_player_pause(&player,0)!=FOJ_PLAYER_OK ||
                foj_player_advance(&player,.125f)!=FOJ_PLAYER_OK ||
                foj_player_pause(&player,1)!=FOJ_PLAYER_OK)
                {failed=1;break;}
        }
        if (!player.paused &&
            foj_player_advance(&player,1.f/60.f)!=FOJ_PLAYER_OK)
            {failed=1;break;}
        if (!pose_vertices(mesh,vertices,bind,&player)){failed=1;break;}

        u32 stride_bytes=0;
        uint32_t *pixels=(uint32_t*)framebufferBegin(&fb,&stride_bytes);
        if (pixels) {
            const int stride=(int)(stride_bytes/sizeof(uint32_t));
            foj_obj_wireframe(mesh,pixels,WIDTH,HEIGHT,stride,
                              .2f,.1f,1.f);
            draw_status(pixels,stride,&player,&clips[0]);
        }
        framebufferEnd(&fb);
    }

    framebufferClose(&fb);
    free(mesh);
    return failed?5:0;
}
