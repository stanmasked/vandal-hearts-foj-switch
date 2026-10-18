#ifndef FOJ_ANIM_PLAYER_H
#define FOJ_ANIM_PLAYER_H

/* Research-only timeline state and local-pose crossfade for BANIM clips.
 * Not a verified reconstruction of the original PS3 actor/blend graph.
 */
#include "skeletal_skin.h"

typedef enum {
    FOJ_PLAYER_OK=0,
    FOJ_PLAYER_ARGUMENT,
    FOJ_PLAYER_MISMATCH,
    FOJ_PLAYER_BUSY,
    FOJ_PLAYER_SAMPLE
} FojPlayerStatus;

typedef struct {
    const FojAnimClip *active;
    const FojAnimClip *incoming;
    size_t bone_count;
    float active_time;
    float incoming_time;
    float fade_elapsed;
    float fade_duration;
    int paused;
} FojAnimPlayer;

/* Clip and bind parents must be exactly equal, including root markers.
 * Caller owns and must keep both clips alive while referenced.
 */
FojPlayerStatus foj_player_init(FojAnimPlayer *player,
    const FojAnimClip *clip, const FojBoneTransform *bind, size_t bones);

FojPlayerStatus foj_player_pause(FojAnimPlayer *player, int paused);

/* Nonnegative, finite delta seconds <= 60. Paused => no time progress.
 * Bad calls leave the player unchanged.
 */
FojPlayerStatus foj_player_advance(FojAnimPlayer *player, float dt);

/* Reject a second transition during an active fade; rejects different
 * parent hierarchies. Zero duration switches immediately.
 */
FojPlayerStatus foj_player_switch(FojAnimPlayer *player,
    const FojAnimClip *next, const FojBoneTransform *bind, size_t bones,
    float fade_seconds);

/* Builds an experimental local-pose blend and original C skin palette.
 * Output remains unchanged if the palette builder rejects a transform.
 */
FojPlayerStatus foj_player_palette(const FojAnimPlayer *player,
    const FojBoneTransform *bind, size_t bones,
    FojSkinMatrix *palette, size_t capacity);

#endif
