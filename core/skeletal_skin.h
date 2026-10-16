#ifndef FOJ_SKELETAL_SKIN_H
#define FOJ_SKELETAL_SKIN_H

/* Experimental platform-independent linear blend skinning.
 *
 * Input Q/XYZ and per-vertex bone/weight layouts match *observed* BMODEL
 * and BANIM records. The interpretation of BANIM translation as absolute
 * local pose, multiplication order and inverse bind usage is a research
 * hypothesis, NOT confirmed original PS3 engine behavior.
 *
 * No original game asset bytes included.
 */
#include <stddef.h>
#include <stdint.h>
#include "banim_core.h"

enum { FOJ_SKIN_MAX_BONES = 256, FOJ_SKIN_MAX_INFLUENCES = 5 };

typedef struct {
    int parent;               /* -1 denotes root; parent < current index */
    float rotation_xyzw[4];
    float translation_xyz[3];
} FojBoneTransform;

typedef struct {
    /* Row-major affine 3x4, point p => m(row)*[x,y,z,1]. */
    float m[12];
} FojSkinMatrix;

typedef struct {
    uint16_t bone;
    float weight;
} FojSkinInfluence;

typedef struct {
    float xyz[3];
    unsigned influence_count; /* 0 means non-skinned rigid vertex */
    FojSkinInfluence influences[FOJ_SKIN_MAX_INFLUENCES];
} FojSkinnedVertex;

typedef enum {
    FOJ_SKIN_OK = 0,
    FOJ_SKIN_ARGUMENT,
    FOJ_SKIN_BOUNDS,
    FOJ_SKIN_HIERARCHY,
    FOJ_SKIN_TRANSFORM,
    FOJ_SKIN_WEIGHTS,
    FOJ_SKIN_MISMATCH
} FojSkinStatus;

/* Builds palette[i] = animatedWorld[i] * inverse(bindWorld[i]).
 * Exact bind pose must produce identity matrices, including multi-root rigs.
 * Requires parent hierarchy identical in both input arrays.
 */
FojSkinStatus foj_skin_build_palette(
    const FojBoneTransform *bind_local,
    const FojBoneTransform *animated_local, size_t bone_count,
    FojSkinMatrix *palette, size_t palette_capacity);

/* Calculate skin weights against the palette. Unweighted vertices retain
 * original position. Output is packed XYZXYZ.., capacity in number of floats.
 * No writes are made if input or any influence is invalid.
 */
FojSkinStatus foj_skin_deform(
    const FojSkinnedVertex *vertices, size_t vertex_count,
    const FojSkinMatrix *palette, size_t bone_count,
    float *output_xyz, size_t output_capacity_floats);

/* Convenience integration: checks BANIM parents against BMODEL skeleton,
 * samples each track at time_seconds using native BANIM slerp and converts
 * the sampled local Q/XYZ into a skinning palette. Track-to-bone mapping
 * is assumed by index, and therefore *must be independently verified* for
 * real model/clip pairs before use as an authentic playback pipeline.
 */
FojSkinStatus foj_skin_sample_palette(
    const FojBoneTransform *bind_local, size_t bone_count,
    const FojAnimClip *clip, float seconds,
    FojSkinMatrix *palette, size_t capacity);

#endif
