#ifndef FOJ_BANIM_CORE_H
#define FOJ_BANIM_CORE_H

/* Platform-independent original-format FoJ BANIM research reader and
 * local pose sampler. No copyrighted motion data is built in.
 * Derived by checking all 450 original NPEB00148 BANIM resources.
 * NOT original game's blending/skin matrix implementation.
 */
#include <stddef.h>
#include <stdint.h>

enum {
    FOJ_BANIM_MAX_TRACKS = 256,
    FOJ_BANIM_MAX_KEYS = 100000,
    FOJ_BANIM_MAX_FILE_BYTES = 8000000
};

typedef struct {
    float time;
    float quat_xyzw[4];
    float translation_xyz[3];
} FojAnimKey;

typedef struct {
    int parent;  /* -1 = root, otherwise index < track index */
    size_t count;
    FojAnimKey *keys;
} FojAnimTrack;

typedef struct {
    float duration;
    size_t track_count;
    FojAnimTrack *tracks;
} FojAnimClip;

typedef struct {
    float quat_xyzw[4];
    float translation_xyz[3];
} FojLocalPose;

typedef enum {
    FOJ_ANIM_OK = 0,
    FOJ_ANIM_ARGUMENT,
    FOJ_ANIM_FORMAT,
    FOJ_ANIM_LIMIT,
    FOJ_ANIM_MEMORY,
    FOJ_ANIM_CAPACITY
} FojAnimStatus;

/* out must be zero-initialized; free any existing contents first.
 * On failure, all partially allocated buffers are released. */
FojAnimStatus foj_banim_parse(const uint8_t *bytes, size_t length,
                              FojAnimClip *out);
void foj_banim_free(FojAnimClip *clip);

/* Independent linear translation + quaternion slerp (research choice).
 * Poses remain LOCAL to their respective bones; no world matrices or skinning
 * applied. Result length must be at least clip->track_count.
 * Each track is clamped to its own available timestamp interval. */
FojAnimStatus foj_banim_sample(const FojAnimClip *clip, float seconds,
                               FojLocalPose *out, size_t capacity);

#endif
