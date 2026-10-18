#ifndef FOJ_RIGGED_ACTOR_SESSION_H
#define FOJ_RIGGED_ACTOR_SESSION_H

/* Stage 194: borrowed user-local model + one/two BANIM playback session.
 * No proprietary source data is embedded. Topology validation is ONLY
 * structural eligibility, never proof of authentic PS3 actor/clip pairing.
 */
#include "rigmesh_io.h"
#include "anim_player.h"

typedef enum {
    FOJ_ACTOR_OK=0,
    FOJ_ACTOR_ARGUMENT,
    FOJ_ACTOR_PRIMARY_INVALID,
    FOJ_ACTOR_SECONDARY_INVALID,
    FOJ_ACTOR_PLAYBACK_ERROR,
    FOJ_ACTOR_SKIN_ERROR
} FojActorStatus;

typedef struct {
    const FojRigMesh *rig;
    const FojAnimClip *primary;
    const FojAnimClip *secondary; /* NULL allows legacy one-clip viewing */
    FojAnimPlayer player;
} FojActorSession;

/* Atomic intake: on any error, *session is unchanged. Caller owns and
 * preserves all three source objects until this session is released.
 */
FojActorStatus foj_actor_init(FojActorSession *session,
    const FojRigMesh *rig, const FojAnimClip *primary,
    const FojAnimClip *secondary);

/* Reset to primary at t=0, paused. Switching changes clips at a research
 * 0.5 second fade; no loops, root motion or original blend graph inferred.
 */
FojActorStatus foj_actor_reset(FojActorSession *session);
FojActorStatus foj_actor_switch(FojActorSession *session, float fade_seconds);

/* Computes weighted XYZ using experimental bone palette; output capacity
 * measured in floats. Reject malformed state before writing any output.
 */
FojActorStatus foj_actor_deform(const FojActorSession *session,
                               float *output_xyz, size_t capacity);

#endif
