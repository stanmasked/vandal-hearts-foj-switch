/* Original-data-capable FoJ rig/animation diagnostic for Nintendo Switch.
 *
 * Loads user-owned local *.fojrm + *.banim from SD; verifies exact ordered
 * bone hierarchy. Recomputes weighted vertex positions with research skin
 * mathematics and renders a CPU wireframe. No game assets bundled.
 *
 * NOT original FoJ shader/animation engine, game UI or playable battle.
 */
#include <switch.h>
#include <math.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "rigmesh_io.h"
#include "skeletal_skin.h"
#include "banim_core.h"
#include "obj_wireframe.h"

enum { FRAME_W = 1280, FRAME_H = 720 };

static int load_file(const char *path, size_t maxbytes,
                     uint8_t **out, size_t *out_length) {
    FILE *file=fopen(path,"rb");
    if (!file) return 0;
    int ok=0;
    if (fseek(file,0,SEEK_END)==0) {
        long size=ftell(file);
        if (size>0 && (size_t)size<=maxbytes && fseek(file,0,SEEK_SET)==0) {
            uint8_t *buffer=malloc((size_t)size);
            if (buffer) {
                if (fread(buffer,1,(size_t)size,file)==(size_t)size) {
                    *out=buffer;
                    *out_length=(size_t)size;
                    ok=1;
                } else free(buffer);
            }
        }
    }
    fclose(file);
    return ok;
}

static int open_rig_clip(FojRigMesh *rig,FojAnimClip *clip) {
    const char *mesh_path="sdmc:/switch/foj/rig/preview.fojrm";
    const char *anim_path="sdmc:/switch/foj/anims/preview.banim";
    uint8_t *bytes=NULL;
    size_t length=0;
    if (!load_file(mesh_path,FOJ_RIGMESH_MAX_FILE_BYTES,&bytes,&length))
        return 0;
    FojRigMeshStatus status=foj_rigmesh_parse(bytes,length,rig);
    free(bytes);
    if (status!=FOJ_RIGMESH_OK) return 0;
    bytes=NULL;
    length=0;
    if (!load_file(anim_path,FOJ_BANIM_MAX_FILE_BYTES,&bytes,&length))
        return 0;
    FojAnimStatus clip_status=foj_banim_parse(bytes,length,clip);
    free(bytes);
    if (clip_status!=FOJ_ANIM_OK) return 0;
    return foj_rigmesh_clip_matches(rig,clip);
}

static FojObjMesh *make_wireframe(const FojRigMesh *source) {
    if (source->vertex_count>FOJ_OBJ_MAX_VERTICES ||
        source->vertex_count/3>FOJ_OBJ_MAX_TRIANGLES)
        return NULL;
    FojObjMesh *mesh=calloc(1,sizeof(*mesh));
    if (!mesh) return NULL;
    mesh->vertex_count=source->vertex_count;
    mesh->triangle_count=source->vertex_count/3;
    float lo[3]={INFINITY,INFINITY,INFINITY};
    float hi[3]={-INFINITY,-INFINITY,-INFINITY};
    for (size_t i=0;i<source->vertex_count;++i) {
        const FojSkinnedVertex *v=&source->vertices[i];
        mesh->vertices[i]=(FojVec3){v->xyz[0],v->xyz[1],v->xyz[2]};
        for (int k=0;k<3;++k) {
            if (v->xyz[k]<lo[k])lo[k]=v->xyz[k];
            if (v->xyz[k]>hi[k])hi[k]=v->xyz[k];
        }
    }
    for (size_t i=0;i<mesh->triangle_count;++i)
        mesh->faces[i]=(FojTri){
            (uint16_t)(3*i),(uint16_t)(3*i+1),(uint16_t)(3*i+2)
        };
    mesh->radius=0;
    for (int k=0;k<3;++k) {
        mesh->center[k]=(lo[k]+hi[k])*.5f;
        float extent=hi[k]-lo[k];
        if (extent>mesh->radius)mesh->radius=extent;
    }
    if (mesh->radius<.00001f)mesh->radius=1.f;
    return mesh;
}

static int update_vertices(const FojRigMesh *rig,const FojAnimClip *clip,
                           FojObjMesh *wire,float seconds,float *positions) {
    FojSkinMatrix palettes[FOJ_SKIN_MAX_BONES];
    if (foj_skin_sample_palette(rig->bind_bones,rig->bone_count,clip,
                                seconds,palettes,rig->bone_count)!=FOJ_SKIN_OK)
        return 0;
    if (foj_skin_deform(rig->vertices,rig->vertex_count,palettes,
                        rig->bone_count,positions,rig->vertex_count*3)
        !=FOJ_SKIN_OK)
        return 0;
    for (size_t i=0;i<rig->vertex_count;++i)
        wire->vertices[i]=(FojVec3){
            positions[3*i],positions[3*i+1],positions[3*i+2]
        };
    return 1;
}

static void missing_files_message(void) {
    consoleInit(NULL);
    padConfigureInput(1,HidNpadStyleSet_NpadStandard);
    PadState pad; padInitializeDefault(&pad);
    printf("FoJ original rigged actor research\n");
    printf("================================\n\n");
    printf("No compatible user-local mesh + animation found.\n");
    printf("Required files on your own SD card:\n\n");
    printf("  /switch/foj/rig/preview.fojrm\n");
    printf("  /switch/foj/anims/preview.banim\n\n");
    printf("Files must have matching bone parent hierarchies.\n");
    printf("This demo includes NO original assets or downloads.\n");
    printf("Use the repo's private local export tools.\n\n");
    printf("Press PLUS to return.\n");
    consoleUpdate(NULL);
    while (appletMainLoop()) {
        padUpdate(&pad);
        if (padGetButtonsDown(&pad)&HidNpadButton_Plus)break;
    }
    consoleExit(NULL);
}

int main(int argc,char **argv) {
    (void)argc;(void)argv;
    FojRigMesh rig={0};
    FojAnimClip clip={0};
    int loaded=open_rig_clip(&rig,&clip);
    if (!loaded && R_SUCCEEDED(fsdevMountSdmc())) {
        foj_rigmesh_free(&rig);
        foj_banim_free(&clip);
        loaded=open_rig_clip(&rig,&clip);
    }
    if (!loaded) {
        missing_files_message();
        foj_rigmesh_free(&rig);
        foj_banim_free(&clip);
        return 0;
    }

    FojObjMesh *view=make_wireframe(&rig);
    float *positions=malloc(rig.vertex_count*3*sizeof(float));
    if (!view || !positions) {
        free(view);free(positions);
        foj_rigmesh_free(&rig);
        foj_banim_free(&clip);
        return 2;
    }

    padConfigureInput(1,HidNpadStyleSet_NpadStandard);
    PadState pad; padInitializeDefault(&pad);
    Framebuffer fb;
    Result result=framebufferCreate(&fb,nwindowGetDefault(),
                                     FRAME_W,FRAME_H,PIXEL_FORMAT_RGBA_8888,2);
    if (R_FAILED(result)) {
        free(view);free(positions);
        foj_rigmesh_free(&rig);foj_banim_free(&clip);
        return 3;
    }
    result=framebufferMakeLinear(&fb);
    if (R_FAILED(result)) {
        framebufferClose(&fb);
        free(view);free(positions);
        foj_rigmesh_free(&rig);foj_banim_free(&clip);
        return 4;
    }
    float yaw=.5f,pitch=.2f,zoom=1.f,t=0.f;
    int playing=0; /* initially static at t=0, wait for user to play */
    while (appletMainLoop()) {
        padUpdate(&pad);
        u64 pressed=padGetButtonsDown(&pad);
        if (pressed&HidNpadButton_Plus)break;
        if (pressed&HidNpadButton_A)playing=!playing;
        if (pressed&HidNpadButton_B) {playing=0;t=0;}
        if (pressed&HidNpadButton_Left)yaw-=.12f;
        if (pressed&HidNpadButton_Right)yaw+=.12f;
        if (pressed&HidNpadButton_Up)pitch+=.12f;
        if (pressed&HidNpadButton_Down)pitch-=.12f;
        if (pressed&HidNpadButton_ZR && zoom<4.f)zoom*=1.25f;
        if (pressed&HidNpadButton_ZL && zoom>.25f)zoom/=1.25f;
        if (pitch>1.5f)pitch=1.5f;
        if (pitch< -1.5f)pitch=-1.5f;
        if (playing && clip.duration>0) {
            t+=1.f/60.f;  /* nominal tick: hardware frame timing unverified */
            if (t>clip.duration)t=0;
        }
        if (!update_vertices(&rig,&clip,view,t,positions))break;

        u32 stride_bytes=0;
        u32 *pixels=(u32 *)framebufferBegin(&fb,&stride_bytes);
        if (pixels) {
            int stride=(int)(stride_bytes/sizeof(u32));
            foj_obj_wireframe(view,(uint32_t *)pixels,
                              FRAME_W,FRAME_H,stride,yaw,pitch,zoom);
            /* Amber = real user-provided input + EXPERIMENTAL bone math.
             * Not green 'authentic PS3 behavior' verification. */
            for (int y=12;y<36;++y)
                for (int x=FRAME_W-48;x<FRAME_W-15;++x)
                    pixels[(size_t)y*(size_t)stride+x]=UINT32_C(0xff57b6e9);
        }
        framebufferEnd(&fb);
    }

    framebufferClose(&fb);
    free(view);free(positions);
    foj_rigmesh_free(&rig);
    foj_banim_free(&clip);
    return 0;
}
