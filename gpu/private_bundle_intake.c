#define _POSIX_C_SOURCE 200809L
#include "private_bundle_intake.h"
#include "material_table.h"
#include "rigmesh_io.h"
#include <errno.h>
#include <fcntl.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <unistd.h>

static int same_file(const struct stat *a,const struct stat *b) {
    return a->st_dev==b->st_dev && a->st_ino==b->st_ino &&
           a->st_mode==b->st_mode && a->st_size==b->st_size &&
           a->st_mtime==b->st_mtime && a->st_ctime==b->st_ctime;
}

/* Read-only: one open descriptor, verify every byte on replay, check
 * descriptor + final named entry and refuse symlinks, directories, FIFOs.
 * Trusted parent directory requirement is documented, not fully enforced;
 * this is no guarantee against adversarial ABA file replacement.
 */
static FojGpuPrivateBundleStatus read_private_regular(
    const char *path,size_t min_len,size_t max_len,
    uint8_t **bytes,size_t *length) {
    if (!path||!bytes||!length)return FOJ_PRIVATE_BUNDLE_ARGUMENT;
    struct stat named;
    if (lstat(path,&named)) {
        return errno==ENOENT ? FOJ_PRIVATE_BUNDLE_MISSING :
                               FOJ_PRIVATE_BUNDLE_IO;
    }
    if (!S_ISREG(named.st_mode))return FOJ_PRIVATE_BUNDLE_PATH_REJECTED;
    if (named.st_size<0 || (uint64_t)named.st_size<min_len ||
        (uint64_t)named.st_size>max_len)return FOJ_PRIVATE_BUNDLE_INVALID;

    int flags=O_RDONLY;
#ifdef O_CLOEXEC
    flags|=O_CLOEXEC;
#endif
#ifdef O_NOFOLLOW
    flags|=O_NOFOLLOW;
#endif
#ifdef O_NONBLOCK
    flags|=O_NONBLOCK;
#endif
    const int fd=open(path,flags);
    if (fd<0)return errno==ELOOP ? FOJ_PRIVATE_BUNDLE_PATH_REJECTED :
                                    FOJ_PRIVATE_BUNDLE_IO;
    struct stat opened;
    if (fstat(fd,&opened) || !S_ISREG(opened.st_mode) ||
        !same_file(&opened,&named)) {
        close(fd);
        return FOJ_PRIVATE_BUNDLE_CHANGED;
    }
    FILE *stream=fdopen(fd,"rb");
    if (!stream) {
        close(fd);
        return FOJ_PRIVATE_BUNDLE_IO;
    }

    const size_t n=(size_t)opened.st_size;
    uint8_t *data=malloc(n);
    FojGpuPrivateBundleStatus result=FOJ_PRIVATE_BUNDLE_MEMORY;
    if (!data)goto done;
    if (fread(data,1,n,stream)!=n) {
        result=FOJ_PRIVATE_BUNDLE_CHANGED;
        goto done;
    }
    if (fseek(stream,0,SEEK_SET)) {
        result=FOJ_PRIVATE_BUNDLE_IO;
        goto done;
    }
    uint8_t chunk[4096];
    for (size_t offset=0;offset<n;) {
        const size_t count=(n-offset)<sizeof(chunk)?(n-offset):sizeof(chunk);
        if (fread(chunk,1,count,stream)!=count ||
            memcmp(chunk,data+offset,count)!=0) {
            result=FOJ_PRIVATE_BUNDLE_CHANGED;
            goto done;
        }
        offset+=count;
    }
    if (fgetc(stream)!=EOF || ferror(stream)) {
        result=FOJ_PRIVATE_BUNDLE_CHANGED;
        goto done;
    }
    struct stat after,again;
    if (fstat(fd,&after) || lstat(path,&again) ||
        !S_ISREG(again.st_mode) || !same_file(&opened,&after) ||
        !same_file(&opened,&again)) {
        result=FOJ_PRIVATE_BUNDLE_CHANGED;
        goto done;
    }
    result=FOJ_PRIVATE_BUNDLE_OK;
done:
    if (fclose(stream))result=FOJ_PRIVATE_BUNDLE_IO;
    if (result==FOJ_PRIVATE_BUNDLE_OK) {
        *bytes=data;*length=n;
    } else free(data);
    return result;
}

const char *foj_gpu_private_bundle_status_name(
    FojGpuPrivateBundleStatus status) {
    switch(status) {
        case FOJ_PRIVATE_BUNDLE_OK:return "private bundle validated";
        case FOJ_PRIVATE_BUNDLE_ARGUMENT:return "invalid arguments";
        case FOJ_PRIVATE_BUNDLE_MISSING:return "required private part missing";
        case FOJ_PRIVATE_BUNDLE_PATH_REJECTED:return "unsafe private path";
        case FOJ_PRIVATE_BUNDLE_IO:return "private file I/O failure";
        case FOJ_PRIVATE_BUNDLE_CHANGED:return "private input changed during read";
        case FOJ_PRIVATE_BUNDLE_INVALID:return "private bundle invalid";
        case FOJ_PRIVATE_BUNDLE_MEMORY:return "private intake allocation failed";
        default:return "unknown private intake result";
    }
}

void foj_gpu_private_bundle_free(FojGpuPrivateBundleData *data) {
    if (!data)return;
    for (unsigned i=0;i<FOJ_GPU_PRIVATE_REQUIRED_ATLASES;++i)
        free(data->rgba[i]);
    free(data->batches);
    free(data->vertices);
    memset(data,0,sizeof(*data));
}

FojGpuPrivateBundleStatus foj_gpu_private_bundle_load(
    const char *mesh_path,const char *material_path,
    const char *const atlas_paths[FOJ_GPU_PRIVATE_REQUIRED_ATLASES],
    const FojTextureCamera *camera,unsigned width,unsigned height,
    size_t gpu_alignment,FojGpuPrivateBundleData *out) {
    if (!mesh_path || !material_path || !atlas_paths ||
        !camera || !out)
        return FOJ_PRIVATE_BUNDLE_ARGUMENT;
    /* Reject missing slots and live caller-owned output before allocation. */
    if (out->vertices || out->batches)return FOJ_PRIVATE_BUNDLE_ARGUMENT;
    for (unsigned i=0;i<FOJ_GPU_PRIVATE_REQUIRED_ATLASES;++i) {
        if (!atlas_paths[i] || out->rgba[i])
            return FOJ_PRIVATE_BUNDLE_ARGUMENT;
    }

    uint8_t *mesh=NULL,*material=NULL;
    size_t mesh_len=0,material_len=0;
    FojGpuPrivateBundleData candidate={0};
    FojGpuPrivateBundleStatus status=read_private_regular(
        mesh_path,28,FOJ_RIGMESH_MAX_FILE_BYTES,&mesh,&mesh_len);
    if (status!=FOJ_PRIVATE_BUNDLE_OK)goto done;
    status=read_private_regular(material_path,20,
             16u+4u*FOJ_MAT_MAX_SECTIONS,&material,&material_len);
    if (status!=FOJ_PRIVATE_BUNDLE_OK)goto done;
    FojMaterialTable table={0};
    if (foj_material_table_parse(material,material_len,&table)!=0 ||
        table.texture_count!=FOJ_GPU_PRIVATE_REQUIRED_ATLASES) {
        status=FOJ_PRIVATE_BUNDLE_INVALID;
        goto done;
    }
    candidate.vertices=malloc(FOJ_GPU_MAX_VERTICES*sizeof(*candidate.vertices));
    candidate.batches=malloc(FOJ_GPU_MAX_BATCHES*sizeof(*candidate.batches));
    if (!candidate.vertices || !candidate.batches) {
        status=FOJ_PRIVATE_BUNDLE_MEMORY;
        goto done;
    }
    if (foj_gpu_private_actor_prepare(mesh,mesh_len,material,material_len,
        camera,width,height,gpu_alignment,candidate.vertices,
        FOJ_GPU_MAX_VERTICES,candidate.batches,FOJ_GPU_MAX_BATCHES,
        &candidate.report.actor)!=FOJ_GPU_STREAM_OK) {
        status=FOJ_PRIVATE_BUNDLE_INVALID;
        goto done;
    }
    for(unsigned i=0;i<FOJ_GPU_PRIVATE_REQUIRED_ATLASES;++i) {
        candidate.rgba[i]=malloc(FOJ_ATLAS_MAX_BYTES);
        if (!candidate.rgba[i]) {
            status=FOJ_PRIVATE_BUNDLE_MEMORY;
            goto done;
        }
        FojAtlasDdsStatus ds=FOJ_ATLAS_DDS_INVALID_ARGUMENT;
        FojAtlasRgba8Info info={0};
        const int loaded=foj_atlas_dds_try_read_status(
            atlas_paths[i],candidate.rgba[i],FOJ_ATLAS_MAX_BYTES,&info,&ds);
        if (loaded!=1 || ds!=FOJ_ATLAS_DDS_LOADED) {
            switch(ds) {
                case FOJ_ATLAS_DDS_MISSING:
                    status=FOJ_PRIVATE_BUNDLE_MISSING;break;
                case FOJ_ATLAS_DDS_PATH_REJECTED:
                    status=FOJ_PRIVATE_BUNDLE_PATH_REJECTED;break;
                case FOJ_ATLAS_DDS_SOURCE_CHANGED:
                    status=FOJ_PRIVATE_BUNDLE_CHANGED;break;
                case FOJ_ATLAS_DDS_IO_FAILURE:
                    status=FOJ_PRIVATE_BUNDLE_IO;break;
                default:
                    status=FOJ_PRIVATE_BUNDLE_INVALID;break;
            }
            goto done;
        }
        candidate.report.atlas[i]=info;
    }
    candidate.report.atlas_count=FOJ_GPU_PRIVATE_REQUIRED_ATLASES;
    *out=candidate;
    memset(&candidate,0,sizeof(candidate)); /* ownership transferred */
    status=FOJ_PRIVATE_BUNDLE_OK;
done:
    foj_gpu_private_bundle_free(&candidate);
    free(material);
    free(mesh);
    return status;
}

FojGpuPrivateBundleStatus foj_gpu_private_bundle_preflight(
    const char *mesh_path,const char *material_path,
    const char *const atlas_paths[FOJ_GPU_PRIVATE_REQUIRED_ATLASES],
    const FojTextureCamera *camera,unsigned width,unsigned height,
    size_t gpu_alignment,FojGpuPrivateBundleReport *report) {
    if (!report)return FOJ_PRIVATE_BUNDLE_ARGUMENT;
    FojGpuPrivateBundleData data={0};
    const FojGpuPrivateBundleStatus result=foj_gpu_private_bundle_load(
        mesh_path,material_path,atlas_paths,camera,width,height,
        gpu_alignment,&data);
    if (result==FOJ_PRIVATE_BUNDLE_OK)*report=data.report;
    foj_gpu_private_bundle_free(&data);
    return result;
}
