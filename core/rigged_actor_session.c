#include "rigged_actor_session.h"

#include <stdint.h>
#include <string.h>

static int valid_rig(const FojRigMesh *rig) {
    return rig && rig->bind_bones && rig->vertices &&
           rig->bone_count && rig->bone_count<=FOJ_SKIN_MAX_BONES &&
           rig->vertex_count>=3 &&
           rig->vertex_count<=FOJ_RIGMESH_MAX_VERTICES &&
           rig->vertex_count%3==0;
}

FojActorStatus foj_actor_init(FojActorSession *session,
    const FojRigMesh *rig, const FojAnimClip *primary,
    const FojAnimClip *secondary) {
    if (!session || !rig || !primary) return FOJ_ACTOR_ARGUMENT;
    if (!valid_rig(rig) ||
        !foj_rigmesh_clip_matches(rig,primary))
        return FOJ_ACTOR_PRIMARY_INVALID;

    FojActorSession pending={0};
    if (foj_player_init(&pending.player,primary,rig->bind_bones,
                        rig->bone_count)!=FOJ_PLAYER_OK)
        return FOJ_ACTOR_PRIMARY_INVALID;

    if (secondary) {
        /* The optional second clip is NOT accepted on track-count alone. */
        FojAnimPlayer probe={0};
        if (secondary==primary ||
            !foj_rigmesh_clip_matches(rig,secondary) ||
            foj_player_init(&probe,secondary,rig->bind_bones,
                            rig->bone_count)!=FOJ_PLAYER_OK)
            return FOJ_ACTOR_SECONDARY_INVALID;
    }
    pending.rig=rig;
    pending.primary=primary;
    pending.secondary=secondary;
    pending.player.paused=1; /* initial screenshot must not advance */
    *session=pending;
    return FOJ_ACTOR_OK;
}

FojActorStatus foj_actor_reset(FojActorSession *session) {
    if (!session || !session->rig || !session->primary)
        return FOJ_ACTOR_ARGUMENT;
    FojAnimPlayer reset={0};
    if (foj_player_init(&reset,session->primary,
                        session->rig->bind_bones,
                        session->rig->bone_count)!=FOJ_PLAYER_OK)
        return FOJ_ACTOR_PLAYBACK_ERROR;
    reset.paused=1;
    session->player=reset;
    return FOJ_ACTOR_OK;
}

FojActorStatus foj_actor_switch(FojActorSession *session,
                                 float fade_seconds) {
    if (!session || !session->rig || !session->primary)
        return FOJ_ACTOR_ARGUMENT;
    if (!session->secondary) return FOJ_ACTOR_SECONDARY_INVALID;
    const FojAnimClip *next = session->player.active==session->primary
                            ? session->secondary : session->primary;
    return foj_player_switch(&session->player,next,
                    session->rig->bind_bones,session->rig->bone_count,
                    fade_seconds)==FOJ_PLAYER_OK
           ? FOJ_ACTOR_OK : FOJ_ACTOR_PLAYBACK_ERROR;
}

FojActorStatus foj_actor_deform(const FojActorSession *session,
                               float *output_xyz, size_t capacity) {
    if (!session || !valid_rig(session->rig) || !output_xyz ||
        !session->primary ||
        capacity<session->rig->vertex_count*3)
        return FOJ_ACTOR_ARGUMENT;
    FojSkinMatrix palette[FOJ_SKIN_MAX_BONES];
    if (foj_player_palette(&session->player,
                           session->rig->bind_bones,
                           session->rig->bone_count,
                           palette,FOJ_SKIN_MAX_BONES)!=FOJ_PLAYER_OK)
        return FOJ_ACTOR_PLAYBACK_ERROR;
    return foj_skin_deform(session->rig->vertices,
                          session->rig->vertex_count,palette,
                          session->rig->bone_count,
                          output_xyz,capacity)==FOJ_SKIN_OK
        ? FOJ_ACTOR_OK : FOJ_ACTOR_SKIN_ERROR;
}
