#include "anim_player.h"

#include <math.h>
#include <string.h>

/* The source PS3 blend scheduler is unknown. These are explicit,
 * bounded research choices, not recovered original FoJ engine rules.
 */
static int matching(const FojAnimClip *clip,
                    const FojBoneTransform *bind, size_t bones) {
    if (!clip || !bind || !clip->tracks || clip->track_count!=bones ||
        !bones || bones>FOJ_SKIN_MAX_BONES ||
        !isfinite(clip->duration) || clip->duration<0.f ||
        clip->duration>600.f)
        return 0;
    for (size_t i=0;i<bones;++i) {
        int parent=bind[i].parent;
        if (parent < -1 || (parent>=0 && (size_t)parent>=i) ||
            clip->tracks[i].parent!=parent ||
            !clip->tracks[i].keys || !clip->tracks[i].count)
            return 0;
    }
    return 1;
}

FojPlayerStatus foj_player_init(FojAnimPlayer *player,
    const FojAnimClip *clip, const FojBoneTransform *bind, size_t bones) {
    if (!player || !clip || !bind) return FOJ_PLAYER_ARGUMENT;
    if (!matching(clip,bind,bones)) return FOJ_PLAYER_MISMATCH;
    FojAnimPlayer result={0};
    result.active=clip;
    result.bone_count=bones;
    *player=result;
    return FOJ_PLAYER_OK;
}

FojPlayerStatus foj_player_pause(FojAnimPlayer *player, int paused) {
    if (!player || !player->active) return FOJ_PLAYER_ARGUMENT;
    player->paused=paused!=0;
    return FOJ_PLAYER_OK;
}

FojPlayerStatus foj_player_advance(FojAnimPlayer *player, float dt) {
    if (!player || !player->active || !isfinite(dt) ||
        dt<0.f || dt>60.f)
        return FOJ_PLAYER_ARGUMENT;
    if (player->paused || dt==0.f) return FOJ_PLAYER_OK;
    FojAnimPlayer staged=*player;
    staged.active_time=fminf(staged.active->duration,
                            staged.active_time+dt);
    if (staged.incoming) {
        staged.incoming_time=fminf(staged.incoming->duration,
                                  staged.incoming_time+dt);
        staged.fade_elapsed=fminf(staged.fade_duration,
                                 staged.fade_elapsed+dt);
        if (staged.fade_elapsed>=staged.fade_duration) {
            staged.active=staged.incoming;
            staged.active_time=staged.incoming_time;
            staged.incoming=NULL;
            staged.incoming_time=0.f;
            staged.fade_elapsed=0.f;
            staged.fade_duration=0.f;
        }
    }
    *player=staged;
    return FOJ_PLAYER_OK;
}

FojPlayerStatus foj_player_switch(FojAnimPlayer *player,
    const FojAnimClip *next, const FojBoneTransform *bind, size_t bones,
    float fade_seconds) {
    if (!player || !player->active || !next || !bind ||
        !isfinite(fade_seconds) || fade_seconds<0.f ||
        fade_seconds>60.f)
        return FOJ_PLAYER_ARGUMENT;
    if (player->incoming) return FOJ_PLAYER_BUSY;
    if (player->bone_count!=bones || !matching(next,bind,bones))
        return FOJ_PLAYER_MISMATCH;
    if (fade_seconds==0.f) {
        player->active=next;
        player->active_time=0.f;
        player->incoming=NULL;
        player->incoming_time=0.f;
        player->fade_elapsed=0.f;
        player->fade_duration=0.f;
    } else {
        player->incoming=next;
        player->incoming_time=0.f;
        player->fade_elapsed=0.f;
        player->fade_duration=fade_seconds;
    }
    return FOJ_PLAYER_OK;
}

static int mixed_rotation(const float *from, const float *to,
                          float alpha, float *result) {
    float a[4],b[4],dot=0.f,an=0.f,bn=0.f;
    for (int i=0;i<4;++i) {
        if (!isfinite(from[i]) || !isfinite(to[i]))return 0;
        an+=from[i]*from[i];
        bn+=to[i]*to[i];
    }
    if (!isfinite(an) || !isfinite(bn) ||
        an<0.96f || an>1.04f || bn<0.96f || bn>1.04f)
        return 0;
    for (int i=0;i<4;++i) {
        a[i]=from[i]/sqrtf(an);
        b[i]=to[i]/sqrtf(bn);
        dot+=a[i]*b[i];
    }
    if (dot<0.f) {
        dot=-dot;
        for (int i=0;i<4;++i)b[i]=-b[i];
    }
    if (dot>1.f)dot=1.f;
    float wa=1.f-alpha,wb=alpha;
    if (dot<=0.9995f) {
        float theta=acosf(dot),denom=sinf(theta);
        if (denom>0.00001f) {
            wa=sinf((1.f-alpha)*theta)/denom;
            wb=sinf(alpha*theta)/denom;
        }
    }
    float norm=0.f;
    for (int i=0;i<4;++i) {
        result[i]=wa*a[i]+wb*b[i];
        norm+=result[i]*result[i];
    }
    if (!isfinite(norm) || norm<0.00001f)return 0;
    for (int i=0;i<4;++i)result[i]/=sqrtf(norm);
    return 1;
}

FojPlayerStatus foj_player_palette(const FojAnimPlayer *player,
    const FojBoneTransform *bind, size_t bones,
    FojSkinMatrix *palette, size_t capacity) {
    if (!player || !player->active || !bind || !palette ||
        !matching(player->active,bind,bones) ||
        player->bone_count!=bones || capacity<bones)
        return FOJ_PLAYER_ARGUMENT;
    if (player->incoming && (!matching(player->incoming,bind,bones) ||
        !isfinite(player->fade_duration) ||
        player->fade_duration<=0.f ||
        !isfinite(player->fade_elapsed) ||
        player->fade_elapsed<0.f ||
        player->fade_elapsed>player->fade_duration))
        return FOJ_PLAYER_MISMATCH;

    FojLocalPose current[FOJ_SKIN_MAX_BONES];
    FojLocalPose incoming[FOJ_SKIN_MAX_BONES];
    FojBoneTransform pose[FOJ_SKIN_MAX_BONES];
    if (foj_banim_sample(player->active,player->active_time,
                         current,bones)!=FOJ_ANIM_OK)
        return FOJ_PLAYER_SAMPLE;
    float weight=0.f;
    if (player->incoming) {
        if (foj_banim_sample(player->incoming,player->incoming_time,
                             incoming,bones)!=FOJ_ANIM_OK)
            return FOJ_PLAYER_SAMPLE;
        weight=player->fade_elapsed/player->fade_duration;
    }
    for (size_t i=0;i<bones;++i) {
        pose[i].parent=bind[i].parent;
        for (int axis=0;axis<3;++axis) {
            float value=current[i].translation_xyz[axis];
            if (player->incoming)
                value=value*(1.f-weight)+incoming[i].translation_xyz[axis]*weight;
            pose[i].translation_xyz[axis]=value;
        }
        /* The exact endpoints are identity operations. Bypassing an
         * unnecessary normalize+slerp avoids a visible frame discontinuity
         * at the moment a fade begins or ends. */
        if (player->incoming && weight >= 1.f) {
            memcpy(pose[i].rotation_xyzw,incoming[i].quat_xyzw,
                   sizeof(pose[i].rotation_xyzw));
        } else if (player->incoming && weight > 0.f) {
            if (!mixed_rotation(current[i].quat_xyzw,
                                incoming[i].quat_xyzw,weight,
                                pose[i].rotation_xyzw))
                return FOJ_PLAYER_SAMPLE;
        } else {
            memcpy(pose[i].rotation_xyzw,current[i].quat_xyzw,
                   sizeof(pose[i].rotation_xyzw));
        }
    }
    if (foj_skin_build_palette(bind,pose,bones,palette,capacity)
        !=FOJ_SKIN_OK)
        return FOJ_PLAYER_SAMPLE;
    return FOJ_PLAYER_OK;
}
