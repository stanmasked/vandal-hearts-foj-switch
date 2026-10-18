/* Stage 192: real C timeline controller and skin matrices under pause/resume
 * and clip crossfade. Invented keys/vertices only, never PS3 copyrighted data.
 */
#include "anim_player.h"
#include <assert.h>
#include <math.h>
#include <stdio.h>
#include <string.h>

static void set_key(FojAnimKey *k,float t,float z,float w,float x,float y) {
    memset(k,0,sizeof(*k));
    k->time=t;
    k->quat_xyzw[2]=z;k->quat_xyzw[3]=w;
    k->translation_xyz[0]=x;k->translation_xyz[1]=y;
}
static void setup(FojAnimClip *clip,FojAnimTrack tracks[2],
                  FojAnimKey root[2],FojAnimKey child[2]) {
    tracks[0]=(FojAnimTrack){-1,2,root};
    tracks[1]=(FojAnimTrack){0,2,child};
    *clip=(FojAnimClip){1.f,2,tracks};
}
static void output(const char *label,const FojAnimPlayer *player,
                   const FojBoneTransform *bind,
                   const FojSkinnedVertex *vertex) {
    FojSkinMatrix matrices[2];
    float xyz[3];
    assert(foj_player_palette(player,bind,2,matrices,2)==FOJ_PLAYER_OK);
    assert(foj_skin_deform(vertex,1,matrices,2,xyz,3)==FOJ_SKIN_OK);
    const float blend=player->incoming
        ?player->fade_elapsed/player->fade_duration:0.f;
    const int active=player->active==NULL? -1:
                     player->active->tracks[0].keys[0].translation_xyz[0]==0?
                     0:1;
    printf("STATE %s %d %.9g %.9g %.9g %d\n",label,active,
           (double)player->active_time,
           (double)(player->incoming?player->incoming_time:-1.f),
           (double)blend,player->paused);
    for(int i=0;i<2;++i) {
        printf("M");
        for(int j=0;j<12;++j)printf(" %.9g",(double)matrices[i].m[j]);
        putchar('\n');
    }
    printf("V %.9g %.9g %.9g\n",(double)xyz[0],
           (double)xyz[1],(double)xyz[2]);
    puts("END");
}
int main(void) {
    const float q=sqrtf(.5f);
    FojBoneTransform bind[2]={0};
    bind[0].parent=-1;bind[0].rotation_xyzw[3]=1.f;
    bind[1].parent=0;bind[1].rotation_xyzw[3]=1.f;
    bind[1].translation_xyz[1]=2;

    FojAnimKey ar[2],ac[2],br[2],bc[2];
    set_key(&ar[0],0,0,1,0,0);
    set_key(&ar[1],1,q,q,1,0);
    set_key(&ac[0],0,0,1,0,2);
    set_key(&ac[1],1,q,q,0,2);
    set_key(&br[0],0,q,q,1,0);
    set_key(&br[1],1,-1,0,2,0);
    set_key(&bc[0],0,q,q,0,2);
    set_key(&bc[1],1,-1,0,0,2);
    FojAnimTrack at[2],bt[2];
    FojAnimClip a,b;
    setup(&a,at,ar,ac);setup(&b,bt,br,bc);
    FojSkinnedVertex vertex={0};
    vertex.xyz[0]=1;vertex.xyz[1]=2;
    vertex.influence_count=2;
    vertex.influences[0]=(FojSkinInfluence){0,.25f};
    vertex.influences[1]=(FojSkinInfluence){1,.75f};

    FojAnimPlayer player={0};
    assert(foj_player_init(&player,&a,bind,2)==FOJ_PLAYER_OK);
    output("start",&player,bind,&vertex);

    assert(foj_player_advance(&player,.25f)==FOJ_PLAYER_OK);
    output("run_025",&player,bind,&vertex);
    assert(foj_player_pause(&player,1)==FOJ_PLAYER_OK);
    assert(foj_player_advance(&player,.25f)==FOJ_PLAYER_OK);
    output("paused",&player,bind,&vertex);
    assert(foj_player_pause(&player,0)==FOJ_PLAYER_OK);
    assert(foj_player_advance(&player,.25f)==FOJ_PLAYER_OK);
    output("resumed",&player,bind,&vertex);

    assert(foj_player_advance(&player,-.1f)==FOJ_PLAYER_ARGUMENT);
    assert(foj_player_advance(&player,NAN)==FOJ_PLAYER_ARGUMENT);
    assert(foj_player_advance(&player,70.f)==FOJ_PLAYER_ARGUMENT);
    assert(fabsf(player.active_time-.5f)<.0001f);
    FojAnimTrack wrong_tracks[2]={bt[0],bt[1]};
    wrong_tracks[1].parent=-1;
    FojAnimClip wrong=b;
    wrong.tracks=wrong_tracks;
    assert(foj_player_switch(&player,&wrong,bind,2,.5f)==FOJ_PLAYER_MISMATCH);
    assert(foj_player_switch(&player,&b,bind,2,NAN)==FOJ_PLAYER_ARGUMENT);
    assert(player.incoming==NULL);
    assert(foj_player_switch(&player,&b,bind,2,.5f)==FOJ_PLAYER_OK);
    output("fade_0",&player,bind,&vertex);
    assert(foj_player_switch(&player,&a,bind,2,.1f)==FOJ_PLAYER_BUSY);

    assert(foj_player_advance(&player,.125f)==FOJ_PLAYER_OK);
    output("fade_025",&player,bind,&vertex);
    assert(foj_player_advance(&player,.125f)==FOJ_PLAYER_OK);
    output("fade_050",&player,bind,&vertex);
    assert(foj_player_pause(&player,1)==FOJ_PLAYER_OK);
    assert(foj_player_advance(&player,.125f)==FOJ_PLAYER_OK);
    output("fade_paused",&player,bind,&vertex);
    assert(foj_player_pause(&player,0)==FOJ_PLAYER_OK);
    assert(foj_player_advance(&player,.125f)==FOJ_PLAYER_OK);
    output("fade_075",&player,bind,&vertex);
    assert(foj_player_advance(&player,.125f)==FOJ_PLAYER_OK);
    output("fade_end",&player,bind,&vertex);
    assert(player.incoming==NULL && player.active==&b);
    assert(foj_player_advance(&player,.25f)==FOJ_PLAYER_OK);
    output("run_b075",&player,bind,&vertex);
    assert(foj_player_advance(&player,.5f)==FOJ_PLAYER_OK);
    output("run_b1_clamped",&player,bind,&vertex);

    assert(foj_player_switch(&player,&a,bind,2,0.f)==FOJ_PLAYER_OK);
    output("instant_a",&player,bind,&vertex);
    FojBoneTransform wrong_bind[2]={bind[0],bind[1]};
    wrong_bind[1].parent=-1;
    FojSkinMatrix untouched[2];
    memset(untouched,0x55,sizeof(untouched));
    assert(foj_player_palette(&player,wrong_bind,2,untouched,2)
           !=FOJ_PLAYER_OK);
    for (size_t i=0;i<sizeof(untouched);++i)
        assert(((const unsigned char*)untouched)[i]==0x55);
    assert(foj_player_switch(&player,&b,wrong_bind,2,.5f)
           ==FOJ_PLAYER_MISMATCH);
    assert(player.active==&a);
    puts("GUARDS OK");
    return 0;
}
