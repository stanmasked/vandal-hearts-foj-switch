/*
 * Stage 194: test production actor-session glue with invented bones, mesh
 * and BANIM clips. No original PS3 bytes, file I/O or leaked asset data.
 */
#include "rigged_actor_session.h"

#include <assert.h>
#include <math.h>
#include <stdio.h>
#include <string.h>

static void key(FojAnimKey *k,float time,float qz,float qw,
                float tx,float ty) {
    memset(k,0,sizeof(*k));
    k->time=time;
    k->quat_xyzw[2]=qz;k->quat_xyzw[3]=qw;
    k->translation_xyz[0]=tx;k->translation_xyz[1]=ty;
}
static void clip(FojAnimClip *clip,FojAnimTrack tracks[2],
                 FojAnimKey root[2],FojAnimKey child[2]) {
    tracks[0]=(FojAnimTrack){-1,2,root};
    tracks[1]=(FojAnimTrack){0,2,child};
    *clip=(FojAnimClip){1.f,2,tracks};
}

static void check_close(float a,float b) {
    assert(isfinite(a)&&isfinite(b)&&fabsf(a-b)<.0002f);
}
static int moved(const float *a,const float *b,size_t length) {
    for(size_t i=0;i<length;++i)
        if(fabsf(a[i]-b[i])>.001f)return 1;
    return 0;
}

int main(void) {
    FojBoneTransform binds[2]={0};
    binds[0].parent=-1;binds[0].rotation_xyzw[3]=1.f;
    binds[1].parent=0;binds[1].rotation_xyzw[3]=1.f;
    binds[1].translation_xyz[1]=1.f;

    FojSkinnedVertex verts[6]={0};
    for(size_t i=0;i<6;++i) {
        verts[i].xyz[0]=(i%3==0?-.25f:.25f);
        verts[i].xyz[1]=(i<3?.4f:1.4f);
        verts[i].influence_count=1;
        verts[i].influences[0]=(FojSkinInfluence){(uint16_t)(i<3?0:1),1.f};
    }
    FojRigMesh rig={0};
    rig.bone_count=2;rig.vertex_count=6;
    rig.bind_bones=binds;rig.vertices=verts;

    FojAnimKey ar[2],ac[2],br[2],bc[2];
    key(&ar[0],0,0,1,0,0);
    key(&ar[1],1,0,1,.4f,0);
    key(&ac[0],0,0,1,0,1);
    key(&ac[1],1,.38268343f,.92387953f,0,1);
    key(&br[0],0,-.38268343f,.92387953f,-.3f,0);
    key(&br[1],1,-.5f,.8660254f,-.6f,0);
    key(&bc[0],0,-.5f,.8660254f,0,1);
    key(&bc[1],1,.38268343f,.92387953f,0,1);
    FojAnimTrack at[2],bt[2];
    FojAnimClip a,b;
    clip(&a,at,ar,ac);clip(&b,bt,br,bc);

    FojActorSession session={0};
    assert(foj_actor_init(&session,&rig,&a,&b)==FOJ_ACTOR_OK);
    assert(session.player.paused && session.player.active==&a);
    float first[18],walking[18],zero[18],quarter[18],frozen[18],end[18];
    assert(foj_actor_deform(&session,first,18)==FOJ_ACTOR_OK);
    check_close(first[0],verts[0].xyz[0]);

    /* No mutation on malformed intake, including optional clip shape. */
    FojActorSession snapshot=session;
    FojAnimTrack wrong_tracks[2]={bt[0],bt[1]};
    wrong_tracks[1].parent=-1;
    FojAnimClip wrong=b;wrong.tracks=wrong_tracks;
    assert(foj_actor_init(&session,&rig,&a,&wrong)
           ==FOJ_ACTOR_SECONDARY_INVALID);
    assert(memcmp(&session,&snapshot,sizeof(session))==0);
    FojAnimTrack wrong_primary_tracks[2]={at[0],at[1]};
    wrong_primary_tracks[1].parent=-1;
    FojAnimClip wrong_primary=a;wrong_primary.tracks=wrong_primary_tracks;
    assert(foj_actor_init(&session,&rig,&wrong_primary,&b)
           ==FOJ_ACTOR_PRIMARY_INVALID);
    assert(memcmp(&session,&snapshot,sizeof(session))==0);
    assert(foj_actor_init(&session,&rig,&a,&a)
           ==FOJ_ACTOR_SECONDARY_INVALID);

    assert(foj_player_advance(&session.player,.25f)==FOJ_PLAYER_OK);
    check_close(session.player.active_time,0.f);
    assert(foj_player_pause(&session.player,0)==FOJ_PLAYER_OK);
    assert(foj_player_advance(&session.player,.25f)==FOJ_PLAYER_OK);
    assert(foj_actor_deform(&session,walking,18)==FOJ_ACTOR_OK);
    assert(moved(walking,first,18));
    assert(foj_player_pause(&session.player,1)==FOJ_PLAYER_OK);
    assert(foj_player_advance(&session.player,.25f)==FOJ_PLAYER_OK);
    assert(foj_actor_deform(&session,frozen,18)==FOJ_ACTOR_OK);
    assert(memcmp(frozen,walking,sizeof(frozen))==0);

    assert(foj_actor_switch(&session,.5f)==FOJ_ACTOR_OK);
    assert(foj_actor_deform(&session,zero,18)==FOJ_ACTOR_OK);
    assert(memcmp(zero,walking,sizeof(zero))==0);
    assert(foj_actor_switch(&session,.5f)==FOJ_ACTOR_PLAYBACK_ERROR);
    assert(foj_player_pause(&session.player,0)==FOJ_PLAYER_OK);
    assert(foj_player_advance(&session.player,.125f)==FOJ_PLAYER_OK);
    check_close(session.player.fade_elapsed,.125f);
    assert(foj_actor_deform(&session,quarter,18)==FOJ_ACTOR_OK);
    assert(moved(quarter,walking,18));
    assert(foj_player_pause(&session.player,1)==FOJ_PLAYER_OK);
    assert(foj_player_advance(&session.player,.125f)==FOJ_PLAYER_OK);
    assert(foj_actor_deform(&session,frozen,18)==FOJ_ACTOR_OK);
    assert(memcmp(frozen,quarter,sizeof(frozen))==0);

    assert(foj_player_pause(&session.player,0)==FOJ_PLAYER_OK);
    assert(foj_player_advance(&session.player,.375f)==FOJ_PLAYER_OK);
    assert(!session.player.incoming && session.player.active==&b);
    assert(foj_actor_deform(&session,end,18)==FOJ_ACTOR_OK);
    assert(moved(end,quarter,18));
    assert(foj_actor_switch(&session,0.f)==FOJ_ACTOR_OK);
    assert(session.player.active==&a);
    check_close(session.player.active_time,0.f);

    /* Fail without writing, and do not allow a forged second clip. */
    float sentinel[18];
    for(size_t i=0;i<18;++i)sentinel[i]=777.f;
    assert(foj_actor_deform(&session,sentinel,17)==FOJ_ACTOR_ARGUMENT);
    for(size_t i=0;i<18;++i)check_close(sentinel[i],777.f);
    FojSkinInfluence save=verts[0].influences[0];
    verts[0].influences[0].bone=222;
    assert(foj_actor_deform(&session,sentinel,18)==FOJ_ACTOR_SKIN_ERROR);
    for(size_t i=0;i<18;++i)check_close(sentinel[i],777.f);
    verts[0].influences[0]=save;

    FojActorSession single={0};
    assert(foj_actor_init(&single,&rig,&a,NULL)==FOJ_ACTOR_OK);
    assert(foj_actor_switch(&single,.5f)==FOJ_ACTOR_SECONDARY_INVALID);
    assert(single.player.active==&a);
    assert(foj_actor_reset(&session)==FOJ_ACTOR_OK);
    assert(session.player.paused && session.player.active==&a);
    check_close(session.player.active_time,0.f);
    puts("STAGE194 ACTOR SESSION PASS: compatible two clips, guard, pause, fade, reset");
    return 0;
}
