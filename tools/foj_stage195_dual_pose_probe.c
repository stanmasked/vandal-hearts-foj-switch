/* Stage 195: independent Python will check real production C actor-session
 * playback through matrices + vertices. All transforms are invented.
 * No original-game bytes, paths, images, or assets are distributed.
 */
#include "rigged_actor_session.h"

#include <assert.h>
#include <math.h>
#include <stdio.h>
#include <string.h>

enum { BONES=3, VERTS=6 };
static void transform(FojBoneTransform *b,int parent,float x,float y,float z) {
    memset(b,0,sizeof(*b));
    b->parent=parent;
    b->rotation_xyzw[3]=1.f;
    b->translation_xyz[0]=x;b->translation_xyz[1]=y;b->translation_xyz[2]=z;
}
static void key(FojAnimKey *k,float t,float qx,float qy,float qz,float qw,
                float x,float y,float z) {
    memset(k,0,sizeof(*k));k->time=t;
    k->quat_xyzw[0]=qx;k->quat_xyzw[1]=qy;
    k->quat_xyzw[2]=qz;k->quat_xyzw[3]=qw;
    k->translation_xyz[0]=x;k->translation_xyz[1]=y;
    k->translation_xyz[2]=z;
}
static void vertex(FojSkinnedVertex *v,float x,float y,float z,
                   int bone0,float w0,int bone1,float w1) {
    memset(v,0,sizeof(*v));
    v->xyz[0]=x;v->xyz[1]=y;v->xyz[2]=z;
    if(bone0>=0) {
        v->influence_count=1;
        v->influences[0]=(FojSkinInfluence){(unsigned short)bone0,w0};
    }
    if(bone1>=0) {
        v->influence_count=2;
        v->influences[1]=(FojSkinInfluence){(unsigned short)bone1,w1};
    }
}
static void print_state(const char *name,const FojActorSession *session,
                        int is_bind) {
    FojSkinMatrix matrices[BONES];
    float result[VERTS*3];
    if(is_bind) {
        assert(foj_skin_build_palette(session->rig->bind_bones,
            session->rig->bind_bones,BONES,matrices,BONES)==FOJ_SKIN_OK);
        assert(foj_skin_deform(session->rig->vertices,VERTS,matrices,
            BONES,result,VERTS*3)==FOJ_SKIN_OK);
    } else {
        assert(foj_player_palette(&session->player,
            session->rig->bind_bones,BONES,matrices,BONES)==FOJ_PLAYER_OK);
        assert(foj_actor_deform(session,result,VERTS*3)==FOJ_ACTOR_OK);
    }
    const FojAnimPlayer *p=&session->player;
    const char *active=p->active==session->primary?"A":"B";
    const float incoming_time=p->incoming?p->incoming_time:-1.f;
    const float alpha=p->incoming?p->fade_elapsed/p->fade_duration:0.f;
    printf("STATE %s %s %.9g %.9g %.9g %d\n",
           name,active,(double)p->active_time,
           (double)incoming_time,(double)alpha,p->paused);
    for(int i=0;i<BONES;++i) {
        putchar('M');
        for(int j=0;j<12;++j)
            printf(" %.9g",(double)matrices[i].m[j]);
        putchar('\n');
    }
    for(int i=0;i<VERTS;++i)
        printf("V %.9g %.9g %.9g\n",
               (double)result[3*i],(double)result[3*i+1],
               (double)result[3*i+2]);
    puts("END");
}
int main(void) {
    const float q=sqrtf(.5f);
    FojBoneTransform bind[BONES];
    transform(&bind[0],-1,2,1,0);
    transform(&bind[1],0,0,2,0);
    transform(&bind[2],-1,-4,0,1);
    FojSkinnedVertex vertices[VERTS];
    vertex(&vertices[0],3,1,0,0,1,-1,0);
    vertex(&vertices[1],3,3,0,1,1,-1,0);
    vertex(&vertices[2],-4,0,1,2,1,-1,0);
    vertex(&vertices[3],4,3,0,0,.25f,1,.75f);
    vertex(&vertices[4],-2,1,1,1,.4f,2,.6f);
    vertex(&vertices[5],0,0,0,-1,0,-1,0); /* unweighted */
    FojRigMesh rig={0};
    rig.bone_count=BONES;rig.vertex_count=VERTS;
    rig.bind_bones=bind;rig.vertices=vertices;

    FojAnimKey a0[3],a1[2],a2[2],b0[2],b1[2],b2[2];
    key(&a0[0],0,0,0,0,1,2,1,0);
    key(&a0[1],.5f,0,0,q,q,3,1,0);
    key(&a0[2],1,0,0,1,0,4,1,0);
    key(&a1[0],-.1f,0,0,0,1,0,2,0);
    key(&a1[1],.8f,q,0,0,q,0,3,0);
    key(&a2[0],0,0,0,0,1,-4,0,1);
    key(&a2[1],1,0,0,0,-1,-3,0,1);
    key(&b0[0],0,0,0,-q,q,1,1,0);
    key(&b0[1],1,0,0,-1,0,0,1,0);
    key(&b1[0],0,0,q,0,q,0,2,0);
    key(&b1[1],1,q,0,0,q,0,2,1);
    key(&b2[0],0,0,0,q,q,-4,1,1);
    key(&b2[1],1,0,0,0,1,-2,0,1);
    FojAnimTrack ta[BONES]={{-1,3,a0},{0,2,a1},{-1,2,a2}};
    FojAnimTrack tb[BONES]={{-1,2,b0},{0,2,b1},{-1,2,b2}};
    FojAnimClip a={1.f,BONES,ta},b={1.f,BONES,tb};
    FojActorSession session={0};
    assert(foj_actor_init(&session,&rig,&a,&b)==FOJ_ACTOR_OK);
    print_state("bind",&session,1);
    print_state("start",&session,0);

    assert(foj_player_pause(&session.player,0)==FOJ_PLAYER_OK);
    assert(foj_player_advance(&session.player,.25f)==FOJ_PLAYER_OK);
    print_state("play025",&session,0);
    assert(foj_player_pause(&session.player,1)==FOJ_PLAYER_OK);
    assert(foj_player_advance(&session.player,.125f)==FOJ_PLAYER_OK);
    print_state("pause025",&session,0);
    assert(foj_player_pause(&session.player,0)==FOJ_PLAYER_OK);
    assert(foj_player_advance(&session.player,.25f)==FOJ_PLAYER_OK);
    print_state("resume050",&session,0);

    assert(foj_player_pause(&session.player,1)==FOJ_PLAYER_OK);
    assert(foj_actor_switch(&session,.5f)==FOJ_ACTOR_OK);
    print_state("fade0",&session,0);
    for(int i=1;i<=2;++i) {
        assert(foj_player_pause(&session.player,0)==FOJ_PLAYER_OK);
        assert(foj_player_advance(&session.player,.125f)==FOJ_PLAYER_OK);
        assert(foj_player_pause(&session.player,1)==FOJ_PLAYER_OK);
        print_state(i==1?"fade025":"fade050",&session,0);
    }
    assert(foj_player_advance(&session.player,.125f)==FOJ_PLAYER_OK);
    print_state("pause050",&session,0);
    assert(foj_player_pause(&session.player,0)==FOJ_PLAYER_OK);
    assert(foj_player_advance(&session.player,.125f)==FOJ_PLAYER_OK);
    print_state("fade075",&session,0);
    assert(foj_player_advance(&session.player,.125f)==FOJ_PLAYER_OK);
    print_state("fade100",&session,0);
    assert(session.player.active==&b && session.player.incoming==NULL);
    assert(foj_player_advance(&session.player,.25f)==FOJ_PLAYER_OK);
    print_state("b075",&session,0);
    assert(foj_player_advance(&session.player,2.f)==FOJ_PLAYER_OK);
    print_state("b_end",&session,0);

    assert(foj_actor_switch(&session,0.f)==FOJ_ACTOR_OK);
    print_state("instant_a",&session,0);
    assert(foj_actor_reset(&session)==FOJ_ACTOR_OK);
    print_state("reset",&session,0);

    /* Bad transition may not overwrite controller state. */
    FojAnimPlayer before=session.player;
    assert(foj_actor_switch(&session,NAN)==FOJ_ACTOR_PLAYBACK_ERROR);
    assert(memcmp(&before,&session.player,sizeof(before))==0);
    puts("GUARDS OK");
    return 0;
}
