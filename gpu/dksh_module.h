#ifndef FOJ_DKSH_MODULE_H
#define FOJ_DKSH_MODULE_H

/* Read-only guard for a generated deko3d DKSH module.
 * Source: devkitPro/deko3d source/dksh.h (24-byte file header,
 * 64-byte program entries, 256-byte-aligned sections).
 * NO proprietary FoJ game data is handled here.
 */
#include <stddef.h>
#include <stdint.h>
enum {
    FOJ_DKSH_VERTEX = 0, FOJ_DKSH_FRAGMENT = 1,
    FOJ_DKSH_MAX_BYTES = 126976, /* <= 128KiB slot minus 1KiB code guard */
};

/* Require a single program at the exact stage. Validates all span math.
 * Does not validate Maxwell instructions; on native Switch deko3d still
 * verifies DKSH at dkShaderInitialize and frame tests remain mandatory.
 */
int foj_dksh_validate(const void *bytes,size_t length,uint32_t expected_type);

/* Copies only an existing user-provided UAM shader file into caller-owned
 * GPU-code-addressable CPU memory. No embedded or downloaded shaders.
 * Returns 0 on missing file, short read, oversize or corrupt metadata.
 */
int foj_dksh_read_file(const char *path,void *dst,size_t capacity,
                       uint32_t stage,size_t *bytes_written);
#endif
