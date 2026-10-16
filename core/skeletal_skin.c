#include "skeletal_skin.h"

#include <math.h>
#include <string.h>

/* Affine 3x4 multiplication: A(B(p)). */
static FojSkinMatrix multiply(const FojSkinMatrix *a, const FojSkinMatrix *b) {
    FojSkinMatrix result;
    for (int row = 0; row < 3; ++row) {
        for (int col = 0; col < 3; ++col) {
            float sum = 0.f;
            for (int k = 0; k < 3; ++k)
                sum += a->m[row*4+k] * b->m[k*4+col];
            result.m[row*4+col] = sum;
        }
        float translation = a->m[row*4+3];
        for (int k = 0; k < 3; ++k)
            translation += a->m[row*4+k]*b->m[k*4+3];
        result.m[row*4+3] = translation;
    }
    return result;
}

static void invert_rigid(const FojSkinMatrix *m, FojSkinMatrix *inverse) {
    /* A normalized quaternion produces orthogonal R, so R^-1 = R^T. */
    for (int i = 0; i < 3; ++i) {
        for (int j = 0; j < 3; ++j)
            inverse->m[i*4+j] = m->m[j*4+i];
    }
    for (int i = 0; i < 3; ++i) {
        float value = 0.f;
        for (int j = 0; j < 3; ++j)
            value -= inverse->m[i*4+j]*m->m[j*4+3];
        inverse->m[i*4+3] = value;
    }
}

static FojSkinStatus bone_to_matrix(const FojBoneTransform *bone,
                                    FojSkinMatrix *out) {
    const float *q = bone->rotation_xyzw;
    float norm = 0.f;
    for (int i=0; i<4; ++i) {
        if (!isfinite(q[i])) return FOJ_SKIN_TRANSFORM;
        norm += q[i]*q[i];
    }
    if (!isfinite(norm) || norm < 0.96f || norm > 1.04f)
        return FOJ_SKIN_TRANSFORM;
    for (int i=0;i<3;++i)
        if (!isfinite(bone->translation_xyz[i]) ||
            fabsf(bone->translation_xyz[i]) > 1000000.f)
            return FOJ_SKIN_TRANSFORM;
    const float inv = 1.f/sqrtf(norm);
    const float x=q[0]*inv, y=q[1]*inv, z=q[2]*inv, w=q[3]*inv;
    out->m[0] = 1.f-2.f*(y*y+z*z);
    out->m[1] = 2.f*(x*y-z*w);
    out->m[2] = 2.f*(x*z+y*w);
    out->m[3] = bone->translation_xyz[0];

    out->m[4] = 2.f*(x*y+z*w);
    out->m[5] = 1.f-2.f*(x*x+z*z);
    out->m[6] = 2.f*(y*z-x*w);
    out->m[7] = bone->translation_xyz[1];

    out->m[8] = 2.f*(x*z-y*w);
    out->m[9] = 2.f*(y*z+x*w);
    out->m[10] = 1.f-2.f*(x*x+y*y);
    out->m[11] = bone->translation_xyz[2];
    return FOJ_SKIN_OK;
}

FojSkinStatus foj_skin_build_palette(
    const FojBoneTransform *bind, const FojBoneTransform *animated,
    size_t n, FojSkinMatrix *palette, size_t capacity) {
    if (!bind || !animated || !palette) return FOJ_SKIN_ARGUMENT;
    if (!n || n > FOJ_SKIN_MAX_BONES || capacity < n) return FOJ_SKIN_BOUNDS;

    FojSkinMatrix bind_world[FOJ_SKIN_MAX_BONES];
    FojSkinMatrix pose_world[FOJ_SKIN_MAX_BONES];
    FojSkinMatrix result[FOJ_SKIN_MAX_BONES];

    for (size_t i=0; i<n; ++i) {
        const int parent = bind[i].parent;
        if (parent < -1 || (parent >= 0 && (size_t)parent >= i) ||
            animated[i].parent != parent)
            return FOJ_SKIN_HIERARCHY;
        FojSkinMatrix bind_local, pose_local;
        FojSkinStatus status = bone_to_matrix(&bind[i], &bind_local);
        if (status != FOJ_SKIN_OK) return status;
        status = bone_to_matrix(&animated[i], &pose_local);
        if (status != FOJ_SKIN_OK) return status;
        if (parent == -1) {
            bind_world[i] = bind_local;
            pose_world[i] = pose_local;
        } else {
            bind_world[i] = multiply(&bind_world[parent], &bind_local);
            pose_world[i] = multiply(&pose_world[parent], &pose_local);
        }
        FojSkinMatrix inverse;
        invert_rigid(&bind_world[i], &inverse);
        result[i] = multiply(&pose_world[i], &inverse);
    }
    memcpy(palette, result, n*sizeof(*palette));
    return FOJ_SKIN_OK;
}

FojSkinStatus foj_skin_deform(
    const FojSkinnedVertex *vertices, size_t n,
    const FojSkinMatrix *palette, size_t bones, float *xyz,
    size_t capacity) {
    if (!vertices || !palette || !xyz) return FOJ_SKIN_ARGUMENT;
    if (bones == 0 || bones > FOJ_SKIN_MAX_BONES ||
        n > (size_t)-1 / 3 || capacity/3 < n)
        return FOJ_SKIN_BOUNDS;
    /* Validate *all* fields first: any error leaves output unchanged. */
    for (size_t i=0; i<bones; ++i)
        for (int j=0; j<12; ++j)
            if (!isfinite(palette[i].m[j]))
                return FOJ_SKIN_TRANSFORM;
    for (size_t i=0; i<n; ++i) {
        const FojSkinnedVertex *v = &vertices[i];
        if (v->influence_count > FOJ_SKIN_MAX_INFLUENCES)
            return FOJ_SKIN_WEIGHTS;
        for (int k=0; k<3; ++k)
            if (!isfinite(v->xyz[k]) || fabsf(v->xyz[k]) > 1000000.f)
                return FOJ_SKIN_TRANSFORM;
        float total = 0.f;
        for (unsigned j=0; j<v->influence_count; ++j) {
            FojSkinInfluence weight=v->influences[j];
            if (weight.bone >= bones || !isfinite(weight.weight) ||
                weight.weight < 0.f || weight.weight > 1.001f)
                return FOJ_SKIN_WEIGHTS;
            total += weight.weight;
        }
        if (v->influence_count && fabsf(total - 1.f) > .002f)
            return FOJ_SKIN_WEIGHTS;
    }
    for (size_t i=0; i<n; ++i) {
        const FojSkinnedVertex *v = &vertices[i];
        if (!v->influence_count) {
            for (int row=0;row<3;++row) xyz[3*i+row]=v->xyz[row];
            continue;
        }
        float accum[3]={0.f,0.f,0.f};
        for (unsigned j=0;j<v->influence_count;++j) {
            const FojSkinMatrix *m = &palette[v->influences[j].bone];
            const float w = v->influences[j].weight;
            for (int row=0;row<3;++row) {
                float transformed = m->m[row*4+3];
                for (int k=0;k<3;++k)
                    transformed += m->m[row*4+k]*v->xyz[k];
                accum[row] += w*transformed;
            }
        }
        for (int row=0;row<3;++row) xyz[3*i+row]=accum[row];
    }
    return FOJ_SKIN_OK;
}

FojSkinStatus foj_skin_sample_palette(
    const FojBoneTransform *bind, size_t n, const FojAnimClip *clip,
    float t, FojSkinMatrix *palette, size_t capacity) {
    if (!bind || !clip || !palette || !isfinite(t))
        return FOJ_SKIN_ARGUMENT;
    if (!n || n > FOJ_SKIN_MAX_BONES || capacity < n)
        return FOJ_SKIN_BOUNDS;
    if (clip->track_count != n || !clip->tracks)
        return FOJ_SKIN_MISMATCH;

    FojLocalPose local[FOJ_SKIN_MAX_BONES];
    FojBoneTransform animated[FOJ_SKIN_MAX_BONES];
    for (size_t i=0;i<n;++i)
        if (clip->tracks[i].parent != bind[i].parent)
            return FOJ_SKIN_MISMATCH;
    if (foj_banim_sample(clip,t,local,n)!=FOJ_ANIM_OK)
        return FOJ_SKIN_MISMATCH;
    for (size_t i=0;i<n;++i) {
        animated[i].parent=bind[i].parent;
        memcpy(animated[i].rotation_xyzw, local[i].quat_xyzw,
               sizeof(animated[i].rotation_xyzw));
        memcpy(animated[i].translation_xyz, local[i].translation_xyz,
               sizeof(animated[i].translation_xyz));
    }
    return foj_skin_build_palette(bind,animated,n,palette,capacity);
}
