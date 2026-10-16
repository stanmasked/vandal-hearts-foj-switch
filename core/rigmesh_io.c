#include "rigmesh_io.h"

#include <math.h>
#include <stdlib.h>
#include <string.h>

static uint32_t read32(const uint8_t *p) {
    return (uint32_t)p[0] | ((uint32_t)p[1]<<8) |
           ((uint32_t)p[2]<<16) | ((uint32_t)p[3]<<24);
}
static float readfloat(const uint8_t *p) {
    const uint32_t bits=read32(p);
    float v;
    memcpy(&v,&bits,sizeof(v));
    return v;
}
static int valid_float(float v) {
    return isfinite(v) && fabsf(v) < 1000000.f;
}
void foj_rigmesh_free(FojRigMesh *m) {
    if (!m) return;
    free(m->bind_bones);
    free(m->vertices);
    free(m->attributes);
    free(m->sections);
    memset(m,0,sizeof(*m));
}

FojRigMeshStatus foj_rigmesh_parse(const uint8_t *data,size_t length,
                                   FojRigMesh *out) {
    if (!data || !out || out->bind_bones || out->vertices ||
        out->attributes || out->sections || out->bone_count ||
        out->vertex_count || out->section_count)
        return FOJ_RIGMESH_ARGUMENT;
    if (length < 28 || length > FOJ_RIGMESH_MAX_FILE_BYTES)
        return FOJ_RIGMESH_LIMIT;
    if (memcmp(data,"FOJRM001",8)!=0 ||
        read32(data+8)!=1 || read32(data+24)!=0)
        return FOJ_RIGMESH_FORMAT;
    const size_t bones=read32(data+12),vertices=read32(data+16);
    const size_t sections=read32(data+20);
    if (!bones || bones>FOJ_SKIN_MAX_BONES ||
        vertices<3 || vertices>FOJ_RIGMESH_MAX_VERTICES ||
        !sections || sections>FOJ_RIGMESH_MAX_SECTIONS ||
        vertices%3)
        return FOJ_RIGMESH_LIMIT;
    const size_t expected=28 + bones*32 + sections*8 + vertices*76;
    if (expected!=length) return FOJ_RIGMESH_FORMAT;
    out->bone_count=bones;
    out->vertex_count=vertices;
    out->section_count=sections;
    out->bind_bones=calloc(bones,sizeof(*out->bind_bones));
    out->vertices=calloc(vertices,sizeof(*out->vertices));
    out->attributes=calloc(vertices,sizeof(*out->attributes));
    out->sections=calloc(sections,sizeof(*out->sections));
    if (!out->bind_bones || !out->vertices || !out->attributes ||
        !out->sections) {
        foj_rigmesh_free(out);
        return FOJ_RIGMESH_MEMORY;
    }
    FojRigMeshStatus error=FOJ_RIGMESH_FORMAT;
    size_t pos=28;
    for (size_t i=0; i<bones; ++i) {
        FojBoneTransform *bone=&out->bind_bones[i];
        const uint32_t parent=read32(data+pos);
        bone->parent=parent==UINT32_MAX ? -1 : (int)parent;
        if (bone->parent < -1 ||
            (bone->parent>=0 && (size_t)bone->parent>=i))
            goto reject;
        pos+=4;
        float norm=0.f;
        for (int j=0;j<4;++j) {
            float v=readfloat(data+pos);pos+=4;
            if (!valid_float(v)) goto reject;
            bone->rotation_xyzw[j]=v;
            norm+=v*v;
        }
        if (fabsf(norm-1.f)>0.04f) goto reject;
        for (int j=0;j<3;++j) {
            float v=readfloat(data+pos);pos+=4;
            if (!valid_float(v)) goto reject;
            bone->translation_xyz[j]=v;
        }
    }
    size_t covered=0;
    for (size_t i=0;i<sections;++i) {
        FojRigSection *s=&out->sections[i];
        s->start_vertex=read32(data+pos);
        s->vertex_count=read32(data+pos+4);
        pos+=8;
        if (s->start_vertex!=covered || !s->vertex_count ||
            s->vertex_count%3 || s->vertex_count>vertices-covered)
            goto reject;
        covered+=s->vertex_count;
    }
    if (covered!=vertices) goto reject;
    for (size_t i=0;i<vertices;++i) {
        FojSkinnedVertex *v=&out->vertices[i];
        FojRigVertexAttributes *attrib=&out->attributes[i];
        for (int j=0;j<3;++j) {
            float x=readfloat(data+pos);pos+=4;
            if (!valid_float(x)) goto reject;
            v->xyz[j]=x;
        }
        for (int j=0;j<2;++j) {
            float x=readfloat(data+pos);pos+=4;
            if (!valid_float(x)) goto reject;
            attrib->uv[j]=x;
        }
        for (int j=0;j<3;++j) {
            float x=readfloat(data+pos);pos+=4;
            if (!valid_float(x)) goto reject;
            attrib->normal[j]=x;
        }
        v->influence_count=read32(data+pos);pos+=4;
        if (v->influence_count>FOJ_SKIN_MAX_INFLUENCES) goto reject;
        float total=0.f;
        for (unsigned j=0;j<FOJ_SKIN_MAX_INFLUENCES;++j) {
            const uint32_t bone=read32(data+pos);
            const float weight=readfloat(data+pos+4);
            pos+=8;
            if (!valid_float(weight) || weight<0.f || weight>1.001f)
                goto reject;
            if (j<v->influence_count) {
                if (bone>=bones) goto reject;
                v->influences[j].bone=(uint16_t)bone;
                v->influences[j].weight=weight;
                total+=weight;
            } else {
                if (bone!=0 || weight!=0.f) goto reject;
            }
        }
        if (v->influence_count && fabsf(total-1.f)>0.002f)
            goto reject;
    }
    if (pos!=length) goto reject;
    return FOJ_RIGMESH_OK;
reject:
    foj_rigmesh_free(out);
    return error;
}

int foj_rigmesh_clip_matches(const FojRigMesh *mesh,const FojAnimClip *clip) {
    if (!mesh || !clip || !mesh->bind_bones || !clip->tracks ||
        !mesh->bone_count || clip->track_count!=mesh->bone_count)
        return 0;
    for (size_t i=0;i<mesh->bone_count;++i)
        if (mesh->bind_bones[i].parent!=clip->tracks[i].parent) return 0;
    return 1;
}
