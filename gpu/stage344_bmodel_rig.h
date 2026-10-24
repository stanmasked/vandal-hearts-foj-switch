#ifndef FOJ_STAGE344_BMODEL_RIG_H
#define FOJ_STAGE344_BMODEL_RIG_H

#include "stage343_bmodel_source.h"

#include <stddef.h>
#include <stdint.h>

#define FOJ_STAGE344_MAX_BONES 256u

typedef struct {
    uint16_t bone_count;
    uint16_t root_count;
    uint16_t skinned_section_count;
    uint16_t out_of_range_skinned_sections;
    uint8_t has_rig;
    uint8_t skin_indices_in_range;
} FojStage344RigSummary;

/* Validate the BMODEL footer and cross-check each skinned section's maximum
 * bone index against the parsed rig count. Footer transforms are validated
 * but not applied. On failure, *out is left unchanged. */
int foj_stage344_bmodel_rig_validate(const uint8_t *data, size_t size,
                                     const FojStage343ModelView *model,
                                     FojStage344RigSummary *out);

/* Safe gate for consumers that intend to submit skinned sections for drawing. */
int foj_stage344_skinning_bones_in_range(const FojStage344RigSummary *summary);

#endif
