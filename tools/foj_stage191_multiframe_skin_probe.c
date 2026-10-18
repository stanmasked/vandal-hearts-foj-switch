/* Stage 191: test multiple BANIM sample times through *production* C
 * animation sampling, world transform composition and weighted skinning.
 * Every key, bone and vertex is invented; no PS3 asset is included.
 */
#include "skeletal_skin.h"

#include <math.h>
#include <stdio.h>
#include <string.h>

#define N_BONES 3
#define N_VERTICES 4
#define N_TIMES 8

static const float TIMES[N_TIMES]={
    -.5f,0.f,.125f,.25f,.5f,.75f,1.f,1.5f
};
static void bone(FojBoneTransform *b,int parent,
                 float x,float y,float z) {
    memset(b,0,sizeof(*b));
    b->parent=parent;
    b->rotation_xyzw[3]=1.f;
    b->translation_xyz[0]=x;
    b->translation_xyz[1]=y;
    b->translation_xyz[2]=z;
}
static void key(FojAnimKey *k,float time,float z,float w,
                float x,float y,float h) {
    memset(k,0,sizeof(*k));
    k->time=time;
    k->quat_xyzw[2]=z;k->quat_xyzw[3]=w;
    k->translation_xyz[0]=x;
    k->translation_xyz[1]=y;
    k->translation_xyz[2]=h;
}
static void weigh(FojSkinnedVertex *v,float x,float y,float z,
                  int b0,float w0,int b1,float w1) {
    memset(v,0,sizeof(*v));
    v->xyz[0]=x;v->xyz[1]=y;v->xyz[2]=z;
    if(b0>=0) {
        v->influences[0].bone=(unsigned short)b0;
        v->influences[0].weight=w0;
        v->influence_count=1;
    }
    if(b1>=0) {
        v->influences[1].bone=(unsigned short)b1;
        v->influences[1].weight=w1;
        v->influence_count=2;
    }
}
int main(void) {
    const float q=sqrtf(.5f);
    FojBoneTransform bind[N_BONES];
    bone(&bind[0],-1,2,1,0);
    bone(&bind[1],0,0,2,0);
    bone(&bind[2],-1,-4,0,1);

    FojAnimKey root[3],child[2],second_root[2];
    key(&root[0],0,0,1,2,1,0);
    key(&root[1],.5f,q,q,3,1,0);
    key(&root[2],1,1,0,4,1,0);
    key(&child[0],.25f,0,1,0,2,0);
    /* Child uses X rotation at t=.75; independent from root Z. */
    key(&child[1],.75f,0,q,0,3,0);
    child[1].quat_xyzw[0]=q;
    key(&second_root[0],0,0,1,-4,0,1);
    key(&second_root[1],1,0,-1,-3,0,1);
    FojAnimTrack tracks[N_BONES]={
        {-1,3,root},{0,2,child},{-1,2,second_root}
    };
    FojAnimClip clip={1.f,N_BONES,tracks};

    FojSkinnedVertex vertices[N_VERTICES]={0};
    weigh(&vertices[0],3,1,0,0,1,-1,0);
    weigh(&vertices[1],3,3,0,1,1,-1,0);
    weigh(&vertices[2],-4,0,1,2,1,-1,0);
    weigh(&vertices[3],4,3,0,0,.25f,1,.75f);

    for(unsigned frame=0;frame<N_TIMES;++frame) {
        const float t=TIMES[frame];
        FojSkinMatrix palette[N_BONES];
        float xyz[N_VERTICES*3];
        if(foj_skin_sample_palette(bind,N_BONES,&clip,t,palette,N_BONES)
           !=FOJ_SKIN_OK)return 2;
        if(foj_skin_deform(vertices,N_VERTICES,palette,N_BONES,
                           xyz,N_VERTICES*3)!=FOJ_SKIN_OK)return 3;
        if(printf("FRAME %u %.9g %d %d\n",frame,(double)t,
                  N_BONES,N_VERTICES)<0)return 4;
        for(unsigned i=0;i<N_BONES;++i) {
            if(printf("M")<0)return 4;
            for(unsigned j=0;j<12;++j) {
                if(!isfinite(palette[i].m[j]))return 5;
                if(printf(" %.9g",(double)palette[i].m[j])<0)return 4;
            }
            if(putchar('\n')==EOF)return 4;
        }
        for(unsigned i=0;i<N_VERTICES;++i) {
            if(!isfinite(xyz[3*i]) || !isfinite(xyz[3*i+1]) ||
               !isfinite(xyz[3*i+2]))return 5;
            if(printf("V %.9g %.9g %.9g\n",
                      (double)xyz[3*i],(double)xyz[3*i+1],
                      (double)xyz[3*i+2])<0)return 4;
        }
        if(puts("END")==EOF)return 4;
    }
    return fflush(stdout)==0?0:4;
}
