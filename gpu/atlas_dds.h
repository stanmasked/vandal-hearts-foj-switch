#ifndef FOJ_ATLAS_DDS_H
#define FOJ_ATLAS_DDS_H
/* Private-user local DDS intake: strict RGBA8, BC1/DXT1 and BC3/DXT5 subset.
 * No PS3 files, codecs, encryption keys or bundled game content. */
#include <stddef.h>
#include <stdint.h>
enum {
    FOJ_ATLAS_DDS_HEADER_BYTES=128,
    FOJ_ATLAS_MAX_WIDTH=256,
    FOJ_ATLAS_MAX_HEIGHT=256,
    FOJ_ATLAS_MAX_BYTES=256*256*4,
    FOJ_ATLAS_MAX_MIP_LEVELS=9,
    /* Full RGBA8 256x256 mip chain is smaller than 1.5x the base. */
    FOJ_ATLAS_MAX_INPUT_BYTES=256*256*4+256*256*2
};
typedef struct {
    unsigned width,height;
    size_t pixel_bytes;
} FojAtlasRgba8Info;

/* Classic DDS only (no DX10, arrays, cubemaps or PS3 swizzling).
 * Input: raw RGBA8/BGRA8, BC1/DXT1 or BC3/DXT5; output is RGBA8 bytes.
 * Width 8..256 multiple of 8; height 1..256, multiple of 4 for BCn.
 * Validates an exact complete mip chain when present, but decodes only
 * level 0. GPU mip filtering/upload remains disabled.
 * On any failure, preserves all output bytes and metadata. */
int foj_atlas_dds_decode(const uint8_t *dds,size_t len,
                         uint8_t *out,size_t cap,FojAtlasRgba8Info *info);

/* Stable generic outcome codes: NEVER include user paths or image bytes.
 * These describe pre-decode intake only, not GPU upload/presentation. */
typedef enum {
    FOJ_ATLAS_DDS_INVALID_ARGUMENT = 0,
    FOJ_ATLAS_DDS_MISSING = 1,
    FOJ_ATLAS_DDS_PATH_REJECTED = 2,
    FOJ_ATLAS_DDS_IO_FAILURE = 3,
    FOJ_ATLAS_DDS_SOURCE_CHANGED = 4,
    FOJ_ATLAS_DDS_INVALID_FORMAT = 5,
    FOJ_ATLAS_DDS_LOADED = 6
} FojAtlasDdsStatus;

/* Optional status output, independently reporting missing/invalid/changed.
 * 1 = loaded; 0 = absent; -1 = rejected or I/O failure.
 * Checks the final path component with lstat and, where supported,
 * O_NOFOLLOW; compares metadata for the opened regular-file descriptor
 * against the path before and after replay. Ancestor path substitution and
 * malicious ABA rewrites are NOT completely excluded by this check.
 * Never modifies pixel or metadata outputs on failure. */
int foj_atlas_dds_try_read_status(const char *path,uint8_t *out,size_t cap,
                                  FojAtlasRgba8Info *info,
                                  FojAtlasDdsStatus *status);

/* Existing API preserved for callers that do not need diagnostics. */
int foj_atlas_dds_try_read(const char *path,uint8_t *out,size_t cap,
                           FojAtlasRgba8Info *info);

/* Stable, path-free English text; safe to print during manual smoke tests. */
const char *foj_atlas_dds_status_name(FojAtlasDdsStatus status);
#endif
