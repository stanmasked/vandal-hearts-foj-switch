/* Stage 200: exercise *real production* rig parsing, BANIM player,
 * CPU skinning and wireframe from a user-LOCAL SD directory on host.
 *
 * All PPM frames may contain user-owned copyrighted geometry: PRIVATE ONLY.
 * No asset bytes, paths or pixel hashes are written to stdout/CI artifacts.
 * This is not the libnx main loop or a PS3-engine accuracy assertion.
 */
#include "rigged_actor_session.h"
#include "obj_wireframe.h"

#include <math.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

enum { W=480, H=320, MAX_PATH=1024, STATES=9 };
static const char *LABELS[STATES]={
    "initial","play_025","paused","fade_0","fade_025",
    "fade_050","fade_075","fade_done","reset"
};

static int make_path(char *out,const char *root,const char *tail) {
    int used=snprintf(out,MAX_PATH,"%s/%s",root,tail);
    return used>0 && used<MAX_PATH;
}

static int read_bounded(const char *path,size_t limit,
                        uint8_t **bytes,size_t *length) {
    FILE *file=fopen(path,"rb");
    if (!file)return 0;
    int result=0;
    if (fseek(file,0,SEEK_END)==0) {
        long n=ftell(file);
        if (n>0 && (unsigned long)n<=limit &&
            fseek(file,0,SEEK_SET)==0) {
            uint8_t *value=malloc((size_t)n);
            if (value) {
                if (fread(value,1,(size_t)n,file)==(size_t)n &&
                    fgetc(file)==EOF && !ferror(file)) {
                    *bytes=value;*length=(size_t)n;result=1;
                } else free(value);
            }
        }
    }
    fclose(file);
    return result;
}

static int read_mesh(const char *root,FojRigMesh *rig) {
    char path[MAX_PATH];
    if (!make_path(path,root,"switch/foj/rig/preview.fojrm"))return 0;
    uint8_t *bytes=NULL;size_t len=0;
    if (!read_bounded(path,FOJ_RIGMESH_MAX_FILE_BYTES,&bytes,&len))return 0;
    FojRigMeshStatus status=foj_rigmesh_parse(bytes,len,rig);
    free(bytes);
    return status==FOJ_RIGMESH_OK;
}

static int read_clip(const char *root,const char *name,
                     FojAnimClip *clip,int required) {
    char path[MAX_PATH],folder[MAX_PATH];
    if (!make_path(folder,root,"switch/foj/anims"))return -1;
    int len=snprintf(path,sizeof(path),"%s/%s",folder,name);
    if (len<=0 || len>=(int)sizeof(path))return -1;
    FILE *probe=fopen(path,"rb");
    if (!probe)return required?-1:0;
    fclose(probe);
    uint8_t *bytes=NULL;size_t size=0;
    if (!read_bounded(path,FOJ_BANIM_MAX_FILE_BYTES,&bytes,&size))return -1;
    FojAnimStatus status=foj_banim_parse(bytes,size,clip);
    free(bytes);
    return status==FOJ_ANIM_OK?1:-1;
}

static FojObjMesh *create_wire(const FojRigMesh *rig) {
    if (!rig || rig->vertex_count>FOJ_OBJ_MAX_VERTICES ||
        rig->vertex_count/3>FOJ_OBJ_MAX_TRIANGLES ||
        rig->vertex_count<3)return NULL;
    FojObjMesh *mesh=calloc(1,sizeof(*mesh));
    if (!mesh)return NULL;
    mesh->vertex_count=rig->vertex_count;
    mesh->triangle_count=rig->vertex_count/3;
    float minv[3]={INFINITY,INFINITY,INFINITY};
    float maxv[3]={-INFINITY,-INFINITY,-INFINITY};
    for(size_t i=0;i<mesh->vertex_count;++i) {
        const float *xyz=rig->vertices[i].xyz;
        mesh->vertices[i]=(FojVec3){xyz[0],xyz[1],xyz[2]};
        for(int j=0;j<3;++j) {
            if(xyz[j]<minv[j])minv[j]=xyz[j];
            if(xyz[j]>maxv[j])maxv[j]=xyz[j];
        }
    }
    for(size_t i=0;i<mesh->triangle_count;++i)
        mesh->faces[i]=(FojTri){
            (uint16_t)(i*3),(uint16_t)(i*3+1),(uint16_t)(i*3+2)
        };
    for(int j=0;j<3;++j){
        mesh->center[j]=(minv[j]+maxv[j])*.5f;
        if(maxv[j]-minv[j]>mesh->radius)
            mesh->radius=maxv[j]-minv[j];
    }
    if(mesh->radius<.00001f)mesh->radius=1.f;
    return mesh;
}

static int render(const char *directory,const char *state,
                  const FojRigMesh *rig,const FojActorSession *session,
                  FojObjMesh *wire,float *xyz,uint32_t *pixels,
                  unsigned *wire_count) {
    if(foj_actor_deform(session,xyz,rig->vertex_count*3)
       !=FOJ_ACTOR_OK)return 0;
    for(size_t i=0;i<rig->vertex_count;++i) {
        for(int j=0;j<3;++j)
            if(!isfinite(xyz[3*i+j]) || fabsf(xyz[3*i+j])>1000000.f)
                return 0;
        wire->vertices[i]=(FojVec3){
            xyz[3*i],xyz[3*i+1],xyz[3*i+2]
        };
    }
    foj_obj_wireframe(wire,pixels,W,H,W,.5f,.2f,1.f);
    unsigned lines=0;
    for(int i=0;i<W*H;++i)
        if(pixels[i]==UINT32_C(0xffbde4da))++lines;
    if(lines<6)return 0;
    *wire_count=lines;
    char path[MAX_PATH];
    if(!make_path(path,directory,state))return 0;
    size_t used=strlen(path);
    if(used+4>=sizeof(path))return 0;
    memcpy(path+used,".ppm",5);
    /* C11 exclusive-create: private screenshots cannot overwrite files. */
    FILE *out=fopen(path,"wbx");
    if(!out)return 0;
    int ok=(fprintf(out,"P6\n%d %d\n255\n",W,H)>0);
    for(int i=0;ok && i<W*H;++i) {
        unsigned char rgb[3]={
            (unsigned char)(pixels[i]&255),
            (unsigned char)((pixels[i]>>8)&255),
            (unsigned char)((pixels[i]>>16)&255)
        };
        if(fwrite(rgb,1,3,out)!=3)ok=0;
    }
    if(fclose(out)!=0)ok=0;
    if(!ok)remove(path);
    return ok;
}

int main(int argc,char **argv) {
    if(argc!=3){
        fputs("usage: actor-smoke <private-sd-root> <private-output-dir>\n",stderr);
        return 2;
    }
    FojRigMesh rig={0};
    FojAnimClip first={0},second={0};
    FojObjMesh *wire=NULL;
    float *xyz=NULL;
    uint32_t *pixels=NULL;
    int exitcode=3,secondary=0;
    unsigned counts[STATES]={0};
    if(!read_mesh(argv[1],&rig))goto done;
    if(read_clip(argv[1],"preview.banim",&first,1)!=1)goto done;
    secondary=read_clip(argv[1],"preview_b.banim",&second,0);
    if(secondary<0)goto done;
    FojActorSession actor={0};
    if(foj_actor_init(&actor,&rig,&first,secondary?&second:NULL)
       !=FOJ_ACTOR_OK)goto done;
    wire=create_wire(&rig);
    xyz=malloc(rig.vertex_count*3*sizeof(float));
    pixels=malloc((size_t)W*H*sizeof(uint32_t));
    if(!wire || !xyz || !pixels)goto done;
    if(!render(argv[2],LABELS[0],&rig,&actor,wire,xyz,pixels,&counts[0]))
        goto done;
    if(foj_player_pause(&actor.player,0)!=FOJ_PLAYER_OK ||
       foj_player_advance(&actor.player,.25f)!=FOJ_PLAYER_OK ||
       foj_player_pause(&actor.player,1)!=FOJ_PLAYER_OK)goto done;
    if(!render(argv[2],LABELS[1],&rig,&actor,wire,xyz,pixels,&counts[1]))
        goto done;
    if(foj_player_advance(&actor.player,.25f)!=FOJ_PLAYER_OK)
        goto done;
    if(!render(argv[2],LABELS[2],&rig,&actor,wire,xyz,pixels,&counts[2]))
        goto done;
    if(foj_actor_reset(&actor)!=FOJ_ACTOR_OK)goto done;
    if(secondary) {
        if(foj_actor_switch(&actor,.5f)!=FOJ_ACTOR_OK)goto done;
    }
    if(!render(argv[2],LABELS[3],&rig,&actor,wire,xyz,pixels,&counts[3]))
        goto done;
    for(int step=1;step<=4;++step) {
        if(foj_player_pause(&actor.player,0)!=FOJ_PLAYER_OK ||
           foj_player_advance(&actor.player,.125f)!=FOJ_PLAYER_OK ||
           foj_player_pause(&actor.player,1)!=FOJ_PLAYER_OK)
           goto done;
        if(!render(argv[2],LABELS[3+step],&rig,&actor,wire,xyz,
                   pixels,&counts[3+step]))goto done;
    }
    if(foj_actor_reset(&actor)!=FOJ_ACTOR_OK)goto done;
    if(!render(argv[2],LABELS[8],&rig,&actor,wire,xyz,pixels,&counts[8]))
        goto done;

    printf("{\"schema\":\"foj.stage200.local_actor_host_smoke.v1\","
           "\"frames_rendered\":%d,\"secondary_clip_used\":%s,"
           "\"rig_bone_count\":%zu,\"vertex_count\":%zu,"
           "\"original_ps3_animation_verified\":false,"
           "\"physical_switch_execution_verified\":false}\n",
           STATES,secondary?"true":"false",rig.bone_count,rig.vertex_count);
    exitcode=0;
done:
    if(exitcode!=0)fputs("Private actor host research smoke rejected.\n",stderr);
    free(pixels);free(xyz);free(wire);
    foj_banim_free(&first);foj_banim_free(&second);
    foj_rigmesh_free(&rig);
    return exitcode;
}
