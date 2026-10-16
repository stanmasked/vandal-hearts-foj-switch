#include "smoke_plan.h"
#include <limits.h>
#include <stddef.h>

static int pow2(uint32_t x) { return x && !(x&(x-1u)); }

int foj_smoke_image_allocation(uint64_t size, uint32_t image_align,
                               uint32_t memory_align, uint32_t *out) {
    if (!out || !size || !pow2(image_align) || !pow2(memory_align))
        return 0;
    uint32_t align=image_align>memory_align?image_align:memory_align;
    if (size>UINT32_MAX-(uint64_t)(align-1u)) return 0;
    uint64_t rounded=(size+(uint64_t)align-1u)&~(uint64_t)(align-1u);
    if (!rounded || rounded>UINT32_MAX) return 0;
    *out=(uint32_t)rounded;
    return 1;
}

int foj_smoke_color(unsigned idx, float out[4]) {
    if (!out || idx>1u) return 0;
    const float intensity=idx ? .35f : .12f;
    out[0]=.09f+intensity;
    out[1]=.12f+.45f*(float)idx;
    out[2]=.23f+.20f*(float)idx;
    out[3]=1.f;
    return 1;
}

unsigned foj_smoke_color_for_frame(uint64_t frame) {
    return (unsigned)((frame/120u)%2u);
}
