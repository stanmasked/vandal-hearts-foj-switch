#ifndef FOJ_MATERIAL_TABLE_H
#define FOJ_MATERIAL_TABLE_H

/* Local-only section -> texture slot map. Not the PS3 material format.
 * Magic "FOJMAT01", LE uint32 section count, texture count, then one
 * LE uint32 texture index per shape/section. No original bytes embedded.
 */
#include <stddef.h>
#include <stdint.h>
enum { FOJ_MAT_MAX_SECTIONS=64, FOJ_MAT_MAX_TEXTURES=8 };

typedef struct {
    size_t section_count, texture_count;
    unsigned section_texture[FOJ_MAT_MAX_SECTIONS];
} FojMaterialTable;

/* 0 = valid, nonzero = unsupported/corrupt. All slots must be referenced. */
int foj_material_table_parse(const uint8_t *bytes,size_t length,
                             FojMaterialTable *out);

#endif
