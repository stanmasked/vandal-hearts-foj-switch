/* Independent research skinning math; all skeletons/vertices invented.
 * No original game resources are embedded in these fixtures.
 */
#include "skeletal_skin.h"

#include <assert.h>
#include <math.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

static const float EPS = 0.0005f;

static int closef(float a, float b) {
    return fabsf(a-b) < EPS;
}
static void identity(FojBoneTransform *b, int parent,
                     float x, float y, float z) {
    memset(b,0,sizeof(*b));
    b->parent=parent;
    b->rotation_xyzw[3]=1.f;
    b->translation_xyz[0]=x;
    b->translation_xyz[1]=y;
    b->translation_xyz[2]=z;
}

static void test_no_movement_in_bind_pose(void) {
    FojBoneTransform bind[3], animated[3];
    identity(&bind[0],-1,10,0,0);
    identity(&bind[1],0,0,2,0);
    identity(&bind[2],-1,-6,0,0); /* second independent root */
    memcpy(animated,bind,sizeof(bind));
    FojSkinMatrix palette[3];
    assert(foj_skin_build_palette(bind,animated,3,palette,3)==FOJ_SKIN_OK);
    for (int i=0;i<3;++i)
        for (int row=0;row<3;++row)
            for (int col=0;col<4;++col) {
                float expected=(col<3 && row==col)?1.f:0.f;
                assert(closef(palette[i].m[row*4+col],expected));
            }
    FojSkinnedVertex vertices[4]={0};
    vertices[0].xyz[0]=11;vertices[0].xyz[1]=2;
    vertices[0].influence_count=1;
    vertices[0].influences[0]=(FojSkinInfluence){1,1.f};
    vertices[1].xyz[0]=-5;vertices[1].influence_count=1;
    vertices[1].influences[0]=(FojSkinInfluence){2,1.f};
    vertices[2].xyz[1]=7; /* no weights; static geometry passthrough */
    vertices[3].xyz[0]=11;vertices[3].xyz[1]=2;
    vertices[3].influence_count=2;
    vertices[3].influences[0]=(FojSkinInfluence){0,.5f};
    vertices[3].influences[1]=(FojSkinInfluence){1,.5f};
    float output[12]={0};
    assert(foj_skin_deform(vertices,4,palette,3,output,12)==FOJ_SKIN_OK);
    for (int i=0;i<4;++i)
        for (int j=0;j<3;++j)
            assert(closef(output[3*i+j],vertices[i].xyz[j]));
}

static void test_joint_rotation_and_weight_blending(void) {
    FojBoneTransform bind[2],animated[2];
    identity(&bind[0],-1,10,0,0);
    identity(&bind[1],0,0,2,0);
    memcpy(animated,bind,sizeof(bind));
    /* 90 degrees about child bone's local Z axis. */
    animated[1].rotation_xyzw[2]=sqrtf(.5f);
    animated[1].rotation_xyzw[3]=sqrtf(.5f);
    FojSkinMatrix matrices[2];
    assert(foj_skin_build_palette(bind,animated,2,matrices,2)==FOJ_SKIN_OK);

    FojSkinnedVertex v[3]={0};
    /* Vertex at (11,2) relative to joint pivot (10,2), so a +90 degree
       rotation yields (10,3). Root-only influence remains (11,2). */
    for (int i=0;i<3;++i) { v[i].xyz[0]=11;v[i].xyz[1]=2; }
    v[0].influence_count=1;
    v[0].influences[0]=(FojSkinInfluence){1,1.f};
    v[1].influence_count=2;
    v[1].influences[0]=(FojSkinInfluence){0,.5f};
    v[1].influences[1]=(FojSkinInfluence){1,.5f};
    v[2].influence_count=1;
    v[2].influences[0]=(FojSkinInfluence){0,1.f};
    float xyz[9]={0};
    assert(foj_skin_deform(v,3,matrices,2,xyz,9)==FOJ_SKIN_OK);
    assert(closef(xyz[0],10) && closef(xyz[1],3));
    assert(closef(xyz[3],10.5f) && closef(xyz[4],2.5f));
    assert(closef(xyz[6],11) && closef(xyz[7],2));
}

static void test_clip_integration_and_parent_guard(void) {
    FojBoneTransform bind[2];
    identity(&bind[0],-1,10,0,0);
    identity(&bind[1],0,0,2,0);
    FojAnimKey root_keys[1]={0};
    root_keys[0].quat_xyzw[3]=1;
    root_keys[0].translation_xyz[0]=10;
    FojAnimKey child_keys[2]={0};
    child_keys[0].quat_xyzw[3]=1;child_keys[0].translation_xyz[1]=2;
    child_keys[1]=child_keys[0];
    child_keys[1].time=1;
    child_keys[1].quat_xyzw[2]=sqrtf(.5f);
    child_keys[1].quat_xyzw[3]=sqrtf(.5f);
    FojAnimTrack tracks[2]={
        {-1,1,root_keys}, {0,2,child_keys}
    };
    FojAnimClip clip={1,2,tracks};
    FojSkinMatrix palette[2];
    assert(foj_skin_sample_palette(bind,2,&clip,0,palette,2)==FOJ_SKIN_OK);
    assert(closef(palette[1].m[0],1));
    assert(foj_skin_sample_palette(bind,2,&clip,1,palette,2)==FOJ_SKIN_OK);
    FojSkinnedVertex point={0};
    point.xyz[0]=11;point.xyz[1]=2;
    point.influence_count=1;
    point.influences[0]=(FojSkinInfluence){1,1.f};
    float xyz[3];
    assert(foj_skin_deform(&point,1,palette,2,xyz,3)==FOJ_SKIN_OK);
    assert(closef(xyz[0],10) && closef(xyz[1],3));

    clip.track_count=1;
    assert(foj_skin_sample_palette(bind,2,&clip,0,palette,2)==FOJ_SKIN_MISMATCH);
    clip.track_count=2;
    tracks[1].parent=-1;
    assert(foj_skin_sample_palette(bind,2,&clip,0,palette,2)==FOJ_SKIN_MISMATCH);
}

static void test_fail_closed_on_invalid_inputs(void) {
    FojBoneTransform bind[2],anim[2];
    identity(&bind[0],-1,0,0,0);
    identity(&bind[1],0,0,0,0);
    memcpy(anim,bind,sizeof(bind));
    FojSkinMatrix palette[2];
    assert(foj_skin_build_palette(bind,anim,2,palette,1)==FOJ_SKIN_BOUNDS);
    bind[1].parent=1;
    assert(foj_skin_build_palette(bind,anim,2,palette,2)==FOJ_SKIN_HIERARCHY);
    bind[1].parent=0;
    anim[1].rotation_xyzw[3]=NAN;
    assert(foj_skin_build_palette(bind,anim,2,palette,2)==FOJ_SKIN_TRANSFORM);
    anim[1].rotation_xyzw[3]=1;
    assert(foj_skin_build_palette(bind,anim,2,palette,2)==FOJ_SKIN_OK);

    FojSkinnedVertex input[2]={0};
    input[0].influence_count=1;
    input[0].influences[0]=(FojSkinInfluence){0,1};
    input[1].influence_count=1;
    input[1].influences[0]=(FojSkinInfluence){8,1};
    float out[6]={31,31,31,31,31,31};
    assert(foj_skin_deform(input,2,palette,2,out,6)==FOJ_SKIN_WEIGHTS);
    for (int j=0;j<6;++j) assert(out[j]==31);
    input[1].influences[0].bone=1;
    input[1].influences[0].weight=.5f;
    assert(foj_skin_deform(input,2,palette,2,out,6)==FOJ_SKIN_WEIGHTS);
    input[1].influences[0].weight=1.f;
    assert(foj_skin_deform(input,2,palette,2,out,5)==FOJ_SKIN_BOUNDS);
    input[0].influence_count=6;
    assert(foj_skin_deform(input,2,palette,2,out,6)==FOJ_SKIN_WEIGHTS);
}

int main(void) {
    test_no_movement_in_bind_pose();
    test_joint_rotation_and_weight_blending();
    test_clip_integration_and_parent_guard();
    test_fail_closed_on_invalid_inputs();
    puts("Skeletal palette/inverse-bind/weighted deformation tests passed");
    return 0;
}
