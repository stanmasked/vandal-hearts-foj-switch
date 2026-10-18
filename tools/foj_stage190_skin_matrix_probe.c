/* Stage 190: independently test production C skeleton palette + CPU skinning.
 * This is a host-only probe, with invented deterministic transforms/vertices.
 * It prints finite row-major floats for an independent Python math oracle.
 */
#include "skeletal_skin.h"

#include <math.h>
#include <stdio.h>
#include <string.h>

#define V 4

static void bone(FojBoneTransform *b,int parent,float x,float y,float z) {
    memset(b,0,sizeof(*b));
    b->parent=parent;
    b->rotation_xyzw[3]=1.f;
    b->translation_xyz[0]=x;
    b->translation_xyz[1]=y;
    b->translation_xyz[2]=z;
}
static void turn(FojBoneTransform *b,int axis,int sign) {
    const float q=sqrtf(.5f);
    memset(b->rotation_xyzw,0,sizeof(b->rotation_xyzw));
    b->rotation_xyzw[axis]=q*(float)sign;
    b->rotation_xyzw[3]=q;
}
static void vertex(FojSkinnedVertex *v,float x,float y,float z) {
    memset(v,0,sizeof(*v));
    v->xyz[0]=x;v->xyz[1]=y;v->xyz[2]=z;
}
static void weight(FojSkinnedVertex *v,unsigned at,
                   unsigned bone_index,float w) {
    v->influences[at].bone=(uint16_t)bone_index;
    v->influences[at].weight=w;
    if (v->influence_count<=at)v->influence_count=at+1u;
}

static int one_case(int index) {
    FojBoneTransform bind[3],anim[3];
    FojSkinnedVertex v[V];
    size_t n=0,nv=0;
    const char *name="";
    memset(v,0,sizeof(v));
    if(index==0) {
        name="bind_multiroot";
        n=3;nv=4;
        bone(&bind[0],-1,10,0,0);
        bone(&bind[1],0,0,2,0);
        bone(&bind[2],-1,-6,0,0);
        memcpy(anim,bind,n*sizeof(*bind));
        vertex(&v[0],11,2,0);weight(&v[0],0,1,1);
        vertex(&v[1],-5,0,0);weight(&v[1],0,2,1);
        vertex(&v[2],0,7,0);
        vertex(&v[3],11,2,0);
        weight(&v[3],0,0,.5f);weight(&v[3],1,1,.5f);
    } else if(index==1) {
        name="child_z90";
        n=2;nv=3;
        bone(&bind[0],-1,10,0,0);
        bone(&bind[1],0,0,2,0);
        memcpy(anim,bind,n*sizeof(*bind));
        turn(&anim[1],2,1);
        vertex(&v[0],11,2,0);weight(&v[0],0,1,1);
        vertex(&v[1],11,2,0);
        weight(&v[1],0,0,.5f);weight(&v[1],1,1,.5f);
        vertex(&v[2],11,2,0);weight(&v[2],0,0,1);
    } else if(index==2) {
        name="two_roots_parent_z90";
        n=3;nv=3;
        bone(&bind[0],-1,2,1,0);
        bone(&bind[1],0,0,2,0);
        bone(&bind[2],-1,-3,0,1);
        memcpy(anim,bind,n*sizeof(*bind));
        turn(&anim[0],2,1);
        anim[1].translation_xyz[1]=3;
        anim[2].translation_xyz[0]=-2;
        vertex(&v[0],2,3,0);weight(&v[0],0,1,1);
        vertex(&v[1],-3,0,1);weight(&v[1],0,2,1);
        vertex(&v[2],5,5,0);
        weight(&v[2],0,0,.25f);weight(&v[2],1,1,.75f);
    } else if(index==3) {
        name="opposite_quaternion_sign";
        n=1;nv=2;
        bone(&bind[0],-1,2,-3,4);
        memcpy(anim,bind,n*sizeof(*bind));
        anim[0].rotation_xyzw[3]=-1.f;
        vertex(&v[0],3,-3,4);weight(&v[0],0,0,1);
        vertex(&v[1],2,-2,4);
    } else if(index==4) {
        name="three_bone_xyz_rotations";
        n=3;nv=3;
        bone(&bind[0],-1,5,2,0);
        bone(&bind[1],0,2,0,0);
        bone(&bind[2],1,0,1,0);
        memcpy(anim,bind,n*sizeof(*bind));
        turn(&anim[0],1,1);
        turn(&anim[1],2,-1);
        turn(&anim[2],0,1);
        anim[2].translation_xyz[2]=1;
        vertex(&v[0],8,3,0);weight(&v[0],0,2,1);
        vertex(&v[1],9,3,1);
        weight(&v[1],0,0,.2f);weight(&v[1],1,1,.3f);
        weight(&v[1],2,2,.5f);
        vertex(&v[2],-1,1,4);
    } else return 1;

    FojSkinMatrix palette[3];
    float output[3*V]={0};
    if(foj_skin_build_palette(bind,anim,n,palette,n)!=FOJ_SKIN_OK ||
       foj_skin_deform(v,nv,palette,n,output,3*nv)!=FOJ_SKIN_OK)
        return 2;
    if(printf("CASE %s %zu %zu\n",name,n,nv)<0)return 3;
    for(size_t i=0;i<n;++i) {
        if(printf("M")<0)return 3;
        for(int k=0;k<12;++k)
            if(printf(" %.9g",(double)palette[i].m[k])<0)return 3;
        if(putchar('\n')==EOF)return 3;
    }
    for(size_t i=0;i<nv;++i) {
        if(printf("V %.9g %.9g %.9g\n",
                  (double)output[3*i],
                  (double)output[3*i+1],
                  (double)output[3*i+2])<0)return 3;
    }
    if(puts("END")==EOF)return 3;
    return 0;
}
int main(void) {
    for(int i=0;i<5;++i)if(one_case(i)!=0)return 2;
    return fflush(stdout)==0?0:2;
}
