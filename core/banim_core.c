#include "banim_core.h"

#include <math.h>
#include <stdlib.h>
#include <string.h>

static uint16_t le16(const uint8_t *p) {
    return (uint16_t)((unsigned)p[0] | ((unsigned)p[1] << 8));
}
static uint32_t le32(const uint8_t *p) {
    return (uint32_t)p[0] | ((uint32_t)p[1]<<8) |
           ((uint32_t)p[2]<<16) | ((uint32_t)p[3]<<24);
}
static float lefloat(const uint8_t *p) {
    const uint32_t bits = le32(p);
    float value = 0.0f;
    memcpy(&value, &bits, sizeof(value));
    return value;
}
static int valid_quat(const float q[4]) {
    float sum = 0.0f;
    for (int i=0;i<4;++i) {
        if (!isfinite(q[i])) return 0;
        sum += q[i]*q[i];
    }
    return fabsf(sum - 1.0f) <= 0.04f;
}

void foj_banim_free(FojAnimClip *clip) {
    if (!clip) return;
    if (clip->tracks) {
        for (size_t i=0; i<clip->track_count; ++i)
            free(clip->tracks[i].keys);
        free(clip->tracks);
    }
    memset(clip, 0, sizeof(*clip));
}

FojAnimStatus foj_banim_parse(const uint8_t *bytes, size_t length,
                              FojAnimClip *out) {
    if (!bytes || !out) return FOJ_ANIM_ARGUMENT;
    if (length < 50 || length > FOJ_BANIM_MAX_FILE_BYTES)
        return FOJ_ANIM_LIMIT;
    if (bytes[0]!=0x0d || bytes[length-1]!=0x13 || sizeof(float)!=4)
        return FOJ_ANIM_FORMAT;
    const float duration = lefloat(bytes+1);
    const uint32_t count = le32(bytes+5);
    if (!isfinite(duration) || duration<0.f || duration>600.f ||
        count<1 || count>FOJ_BANIM_MAX_TRACKS || le16(bytes+9)!=0)
        return FOJ_ANIM_FORMAT;

    /* out must be zeroed/free before invocation. Do not invalidate old
       allocations silently by resetting an already-owned clip. */
    if (out->tracks || out->track_count) return FOJ_ANIM_ARGUMENT;
    out->duration = duration;
    out->track_count = count;
    out->tracks = calloc(count, sizeof(*out->tracks));
    if (!out->tracks) {
        foj_banim_free(out);
        return FOJ_ANIM_MEMORY;
    }
    FojAnimStatus error = FOJ_ANIM_FORMAT;
    size_t pos = 11, total = 0;
    for (size_t track = 0; track < count; ++track) {
        if (pos > length - 1 || length - 1 - pos < 5 ||
            bytes[pos]!=0x11) goto fail;
        const unsigned parent = le16(bytes+pos+1);
        const unsigned n = le16(bytes+pos+3);
        pos += 5;
        if ((parent!=0xffff && parent>=track) || n<1 || n>4096)
            goto fail;
        if (total + n > FOJ_BANIM_MAX_KEYS) {
            error = FOJ_ANIM_LIMIT;
            goto fail;
        }
        total += n;
        if (pos > length - 1 || (size_t)n > (length-1-pos)/33)
            goto fail;
        FojAnimTrack *t = &out->tracks[track];
        t->parent = parent==0xffff ? -1 : (int)parent;
        t->count = n;
        t->keys = calloc(n, sizeof(*t->keys));
        if (!t->keys) {
            error = FOJ_ANIM_MEMORY;
            goto fail;
        }
        float previous = -INFINITY;
        for (unsigned k=0;k<n;++k) {
            if (bytes[pos]!=0x12) goto fail;
            FojAnimKey *key=&t->keys[k];
            key->time = lefloat(bytes+pos+1);
            for (int j=0;j<4;++j)
                key->quat_xyzw[j] = lefloat(bytes+pos+5+4*j);
            for (int j=0;j<3;++j)
                key->translation_xyz[j] = lefloat(bytes+pos+21+4*j);
            pos+=33;
            if (!isfinite(key->time) || key->time< -1.f ||
                key->time>duration+1.f || key->time+0.0001f<previous ||
                !valid_quat(key->quat_xyzw)) goto fail;
            previous=key->time;
            for (int j=0;j<3;++j)
                if (!isfinite(key->translation_xyz[j]) ||
                    fabsf(key->translation_xyz[j])>1000000.f) goto fail;
        }
    }
    if (pos!=length-1) goto fail;
    return FOJ_ANIM_OK;
fail:
    foj_banim_free(out);
    return error;
}

static void copy_pose(const FojAnimKey *key, FojLocalPose *pose) {
    memcpy(pose->quat_xyzw, key->quat_xyzw, sizeof(pose->quat_xyzw));
    memcpy(pose->translation_xyz, key->translation_xyz,
           sizeof(pose->translation_xyz));
}

static void slerp(const float left[4],const float right[4],
                  float alpha,float out[4]) {
    float dot=0.f, q1[4];
    for (int i=0;i<4;++i) {
        q1[i]=right[i];
        dot+=left[i]*q1[i];
    }
    if (dot<0) {
        dot=-dot;
        for (int i=0;i<4;++i) q1[i]=-q1[i];
    }
    if (dot>1.f)dot=1.f;
    float w0=1.f-alpha,w1=alpha;
    if (dot<=0.9995f) {
        const float theta=acosf(dot), sine=sinf(theta);
        if (sine>0.00001f) {
            w0=sinf((1.f-alpha)*theta)/sine;
            w1=sinf(alpha*theta)/sine;
        }
    }
    float norm=0.f;
    for (int i=0;i<4;++i) {
        out[i]=w0*left[i]+w1*q1[i];
        norm+=out[i]*out[i];
    }
    norm=sqrtf(norm);
    if (norm>0.00001f)
        for (int i=0;i<4;++i) out[i]/=norm;
}

FojAnimStatus foj_banim_sample(const FojAnimClip *clip,float seconds,
                               FojLocalPose *out,size_t capacity) {
    if (!clip || !out || !clip->tracks || !isfinite(seconds))
        return FOJ_ANIM_ARGUMENT;
    if (capacity<clip->track_count) return FOJ_ANIM_CAPACITY;
    for (size_t i=0;i<clip->track_count;++i) {
        const FojAnimTrack *track=&clip->tracks[i];
        if (!track->keys || !track->count) return FOJ_ANIM_FORMAT;
        if (seconds<=track->keys[0].time) {
            copy_pose(&track->keys[0],&out[i]);
            continue;
        }
        if (seconds>=track->keys[track->count-1].time) {
            copy_pose(&track->keys[track->count-1],&out[i]);
            continue;
        }
        size_t lo=0,hi=track->count-1;
        while (hi-lo>1) {
            size_t mid=(hi+lo)/2;
            if (track->keys[mid].time<=seconds) lo=mid;
            else hi=mid;
        }
        const FojAnimKey *a=&track->keys[lo],*b=&track->keys[hi];
        float dt=b->time-a->time;
        float alpha=dt>0 ? (seconds-a->time)/dt : 0;
        slerp(a->quat_xyzw,b->quat_xyzw,alpha,out[i].quat_xyzw);
        for (int j=0;j<3;++j)
            out[i].translation_xyz[j] = a->translation_xyz[j]*(1-alpha) +
                                         b->translation_xyz[j]*alpha;
    }
    return FOJ_ANIM_OK;
}
