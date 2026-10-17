/* Validates numeric deko3d shader/device ABI contract with the mock.
 * The optional native NRO includes the same static assertions using the
 * actual SDK deko3d.h. This host test is not a physical GPU test. */
#include <deko3d.h>
#include "deko3d_api_contract.h"
/* Test assertions must also run when the build supplies -DNDEBUG. */
#ifdef NDEBUG
#undef NDEBUG
#endif
#include <assert.h>
#include <stdio.h>

int main(void) {
    /* deko3d selects [0,1] clip Z using ZERO, not a truthy flag bit. */
    DkDeviceMaker zero_to_one={0};
    zero_to_one.flags=DkDeviceFlags_DepthZeroToOne |
        DkDeviceFlags_OriginUpperLeft | DkDeviceFlags_YAxisPointsUp;
    assert(zero_to_one.flags==0u);
    assert((zero_to_one.flags&DkDeviceFlags_DepthMinusOneToOne)==0u);

    DkDeviceMaker minus_one_to_one={0};
    minus_one_to_one.flags=DkDeviceFlags_DepthMinusOneToOne;
    assert(minus_one_to_one.flags==256u);
    assert((minus_one_to_one.flags&DkDeviceFlags_DepthMinusOneToOne)!=0u);

    puts("deko3d ABI: 0..1 depth=0, -1..1 depth=256 (host contract PASS)");
    return 0;
}
