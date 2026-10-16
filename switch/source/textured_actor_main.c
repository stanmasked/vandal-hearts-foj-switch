/* Native original-data FoJ research: CPU textured, skinned 3D actor.
 * Expects all inputs provided by the user on their own Switch SD card.
 * PS3 original shader conventions and game systems are NOT reimplemented.
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
#include "dds_texture.h"
#include "textured_triangles.h"
#include "material_table.h"

enum { VIEW_W=1280, VIEW_H=720, MAX_DDS_SIZE=8388608 };

typedef struct {
    FojMaterialTable mapping;
    FojTexture texture[FOJ_MAT_MAX_TEXTURES];
} FojAtlasSet;

static void clear_atlases(FojAtlasSet *set) {
    if (!set)return;
    for (size_t i=0;i<FOJ_MAT_MAX_TEXTURES;++i)
        free((void*)set->texture[i].rgba);
    memset(set,0,sizeof(*set));
}


static int read_file(const char *path,size_t limit,uint8_t **buf,size_t *len) {
    FILE *file=fopen(path,"rb");
    if (!file)return 0;
    int success=0;
    if (fseek(file,0,SEEK_END)==0) {
        long n=ftell(file);
        if (n>0 && (size_t)n<=limit && fseek(file,0,SEEK_SET)==0) {
            uint8_t *bytes=malloc((size_t)n);
            if (bytes) {
                if (fread(bytes,1,(size_t)n,file)==(size_t)n) {
                    *buf=bytes;*len=(size_t)n;success=1;
                } else free(bytes);
            }
        }
    }
    fclose(file);
    return success;
}

static int load_dds(const char *path,FojTexture *texture) {
    uint8_t *data=NULL;
    size_t len=0;
    if (!read_file(path,MAX_DDS_SIZE,&data,&len))return 0;
    FojDdsInfo info;
    FojDdsStatus check=foj_dds_inspect(data,len,&info);
    if (check!=FOJ_DDS_OK) {free(data);return 0;}
    size_t count=(size_t)info.width*info.height;
    /* Keep bounded memory for multiple simultaneously decoded atlases. */
    if (count > 2097152) {free(data);return 0;}
    uint32_t *rgba=malloc(count*sizeof(*rgba));
    if (!rgba) {free(data);return 0;}
    check=foj_dds_decode(data,len,rgba,info.width,count,&info);
    free(data);
    if (check!=FOJ_DDS_OK) {free(rgba);return 0;}
    *texture=(FojTexture){rgba,info.width,info.height,info.width};
    return 1;
}

/* An optional user-local FOJMAT01 selects a DDS per original shape.
 * Without it, the legacy one-atlas preview.tga is used for every shape. */
static int load_atlases(FojAtlasSet *atlas,size_t expected_sections) {
    const char *manifest="sdmc:/switch/foj/textures/preview.fojmat";
    FILE *probe=fopen(manifest,"rb");
    if (probe) {
        fclose(probe);
        uint8_t *data=NULL;
        size_t length=0;
        if (!read_file(manifest,16+4*FOJ_MAT_MAX_SECTIONS,
                       &data,&length))return 0;
        int okay=foj_material_table_parse(data,length,&atlas->mapping)==0;
        free(data);
        if (!okay || atlas->mapping.section_count!=expected_sections)
            return 0;
        for (size_t i=0;i<atlas->mapping.texture_count;++i) {
            char filename[96];
            snprintf(filename,sizeof(filename),
                     "sdmc:/switch/foj/textures/texture_%02u.tga",
                     (unsigned)i);
            if (!load_dds(filename,&atlas->texture[i]))return 0;
        }
        return 1;
    }
    if (!load_dds("sdmc:/switch/foj/textures/preview.tga",
                  &atlas->texture[0]))return 0;
    atlas->mapping.section_count=expected_sections;
    atlas->mapping.texture_count=1;
    return expected_sections>0 && expected_sections<=FOJ_MAT_MAX_SECTIONS;
}

static int open_local_inputs(FojRigMesh *rig,FojAnimClip *clip,
                             FojAtlasSet *atlas) {
    uint8_t *data=NULL;
    size_t len=0;
    if (!read_file("sdmc:/switch/foj/rig/preview.fojrm",
                   FOJ_RIGMESH_MAX_FILE_BYTES,&data,&len))return 0;
    FojRigMeshStatus mesh_status=foj_rigmesh_parse(data,len,rig);
    free(data);data=NULL;
    if (mesh_status!=FOJ_RIGMESH_OK)return 0;
    if (!read_file("sdmc:/switch/foj/anims/preview.banim",
                   FOJ_BANIM_MAX_FILE_BYTES,&data,&len))return 0;
    FojAnimStatus anim_status=foj_banim_parse(data,len,clip);
    free(data);data=NULL;
    if (anim_status!=FOJ_ANIM_OK || !foj_rigmesh_clip_matches(rig,clip))
        return 0;
    return load_atlases(atlas,rig->section_count);
}

static void show_diagnostic(void) {
    consoleInit(NULL);
    printf("FoJ CPU textured actor research\n\n");
    printf("User-local original game files required:\n\n");
    printf("/switch/foj/rig/preview.fojrm\n");
    printf("/switch/foj/anims/preview.banim\n");
    printf("/switch/foj/textures/preview.tga\n\n");
    printf("No embedded PS3 game assets or automatic downloads.\n");
    printf("Wrong files, incompatible skeletons and missing DDS\n");
    printf("prevent this original-data research viewer starting.\n\n");
    printf("Press PLUS to exit.\n");
    consoleUpdate(NULL);
    padConfigureInput(1,HidNpadStyleSet_NpadStandard);
    PadState pad;padInitializeDefault(&pad);
    while (appletMainLoop()) {
        padUpdate(&pad);
        if (padGetButtonsDown(&pad)&HidNpadButton_Plus)break;
    }
    consoleExit(NULL);
}

static FojTextureCamera camera_for(const FojRigMesh *rig) {
    float low[3]={INFINITY,INFINITY,INFINITY};
    float high[3]={-INFINITY,-INFINITY,-INFINITY};
    for (size_t i=0;i<rig->vertex_count;++i) {
        for (int k=0;k<3;++k) {
            float v=rig->vertices[i].xyz[k];
            if (v<low[k])low[k]=v;
            if (v>high[k])high[k]=v;
        }
    }
    FojTextureCamera c={0};
    for (int k=0;k<3;++k) {
        float delta=high[k]-low[k];
        if (delta>c.extent)c.extent=delta;
    }
    if (c.extent<.00001f)c.extent=1.f;
    c.center_x=(high[0]+low[0])*.5f;
    c.center_y=(high[1]+low[1])*.5f;
    c.center_z=(high[2]+low[2])*.5f;
    c.yaw=.35f;c.pitch=.15f;c.zoom=1.f;
    return c;
}

static int update_geometry(const FojRigMesh *rig,const FojAnimClip *clip,
                           float seconds,FojTexturedVertex *tri,
                           float *positions) {
    FojSkinMatrix palette[FOJ_SKIN_MAX_BONES];
    if (foj_skin_sample_palette(rig->bind_bones,rig->bone_count,clip,
                                seconds,palette,rig->bone_count)!=FOJ_SKIN_OK)
        return 0;
    if (foj_skin_deform(rig->vertices,rig->vertex_count,
                        palette,rig->bone_count,positions,
                        rig->vertex_count*3)!=FOJ_SKIN_OK)
        return 0;
    for (size_t i=0;i<rig->vertex_count;++i) {
        const FojRigVertexAttributes *a=&rig->attributes[i];
        tri[i]=(FojTexturedVertex){
            positions[3*i],positions[3*i+1],positions[3*i+2],
            a->uv[0],a->uv[1]
        };
    }
    return 1;
}

int main(int argc,char **argv) {
    (void)argc;(void)argv;
    FojRigMesh rig={0};FojAnimClip clip={0};FojAtlasSet atlas={0};
    int available=open_local_inputs(&rig,&clip,&atlas);
    if (!available && R_SUCCEEDED(fsdevMountSdmc())) {
        foj_rigmesh_free(&rig);foj_banim_free(&clip);
        clear_atlases(&atlas);
        available=open_local_inputs(&rig,&clip,&atlas);
    }
    if (!available) {
        show_diagnostic();
        foj_rigmesh_free(&rig);foj_banim_free(&clip);
        clear_atlases(&atlas);
        return 0;
    }
    FojTexturedVertex *tri=malloc(rig.vertex_count*sizeof(*tri));
    float *positions=malloc(rig.vertex_count*3*sizeof(*positions));
    float *depth=malloc((size_t)VIEW_W*VIEW_H*sizeof(*depth));
    if (!tri || !positions || !depth) {
        free(tri);free(positions);free(depth);
        foj_rigmesh_free(&rig);foj_banim_free(&clip);
        clear_atlases(&atlas);
        return 2;
    }

    padConfigureInput(1,HidNpadStyleSet_NpadStandard);
    PadState pad;padInitializeDefault(&pad);
    Framebuffer fb;
    Result result=framebufferCreate(&fb,nwindowGetDefault(),
                                    VIEW_W,VIEW_H,PIXEL_FORMAT_RGBA_8888,2);
    if (R_FAILED(result)) {
        free(tri);free(positions);free(depth);
        foj_rigmesh_free(&rig);foj_banim_free(&clip);
        clear_atlases(&atlas);
        return 3;
    }
    result=framebufferMakeLinear(&fb);
    if (R_FAILED(result)) {
        framebufferClose(&fb);
        free(tri);free(positions);free(depth);
        foj_rigmesh_free(&rig);foj_banim_free(&clip);
        clear_atlases(&atlas);
        return 4;
    }
    FojTextureSection shapes[FOJ_MAT_MAX_SECTIONS]={0};
    for (size_t i=0;i<rig.section_count;++i) {
        shapes[i]=(FojTextureSection){
            rig.sections[i].start_vertex,rig.sections[i].vertex_count,
            atlas.mapping.section_texture[i]
        };
    }
    FojTextureCamera camera=camera_for(&rig);
    float time=0.f;
    int playing=0;
    while (appletMainLoop()) {
        padUpdate(&pad);
        u64 keys=padGetButtonsDown(&pad);
        if (keys&HidNpadButton_Plus)break;
        if (keys&HidNpadButton_A)playing=!playing;
        if (keys&HidNpadButton_B){playing=0;time=0;}
        if (keys&HidNpadButton_Left)camera.yaw-=.12f;
        if (keys&HidNpadButton_Right)camera.yaw+=.12f;
        if (keys&HidNpadButton_Up)camera.pitch+=.12f;
        if (keys&HidNpadButton_Down)camera.pitch-=.12f;
        if (keys&HidNpadButton_ZR && camera.zoom<4.f)camera.zoom*=1.25f;
        if (keys&HidNpadButton_ZL && camera.zoom>.25f)camera.zoom/=1.25f;
        if (keys&HidNpadButton_X)camera.flip_v=!camera.flip_v;
        if (keys&HidNpadButton_Y)camera.bilinear=!camera.bilinear;
        if (camera.pitch>1.5f)camera.pitch=1.5f;
        if (camera.pitch< -1.5f)camera.pitch=-1.5f;
        if (playing && clip.duration>0) {
            time+=1.f/60.f; /* approximate; hardware frame timing unverified */
            if (time>clip.duration)time=0;
        }
        if (!update_geometry(&rig,&clip,time,tri,positions))break;
        u32 pitch_bytes=0;
        u32 *pixels=(u32*)framebufferBegin(&fb,&pitch_bytes);
        if (pixels) {
            FojRenderSurface surface={(uint32_t*)pixels,depth,
                VIEW_W,VIEW_H,(unsigned)(pitch_bytes/sizeof(u32)),VIEW_W};
            size_t drawn=0;
            if (foj_textured_render_sections(
                    tri,rig.vertex_count,atlas.texture,
                    atlas.mapping.texture_count,shapes,rig.section_count,
                    &surface,&camera,&drawn)!=FOJ_TEX_OK)
                break;
            /* Amber = original user data + UNVERIFIED FoJ PS3 material math. */
            for (int y=12;y<36;++y)
                for (int x=VIEW_W-48;x<VIEW_W-15;++x)
                    pixels[(size_t)y*surface.color_stride+x]=UINT32_C(0xff57b6e9);
        }
        framebufferEnd(&fb);
    }
    framebufferClose(&fb);
    free(tri);free(positions);free(depth);
    clear_atlases(&atlas);
    foj_rigmesh_free(&rig);foj_banim_free(&clip);
    return 0;
}
