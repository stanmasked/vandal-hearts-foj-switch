/* Stage255 isolated 384-frame tight-budget receipt; synthetic CPU only. */
#include "compact_budget_probe.h"
#include <assert.h>
#include <stdint.h>
#include <stdlib.h>

static void test_384_frame_receipt(void) {
    uint32_t *a=(uint32_t *)calloc(1280u*720u,sizeof(uint32_t));
    uint32_t *b=(uint32_t *)calloc(1280u*720u,sizeof(uint32_t));
    assert(a && b);
    FojBudgetReceipt receipt={0};
    assert(!foj_budget_probe_run(NULL,a,b));
    assert(!foj_budget_probe_run(&receipt,NULL,b));
    assert(!foj_budget_probe_run(&receipt,a,a));
    for(int i=0;i<2;++i) {
        assert(foj_budget_probe_run(&receipt,a,b));
        assert(receipt.passed && receipt.frames==384);
        assert(receipt.allocations==48 && receipt.releases==48);
        assert(receipt.hits==192 && receipt.misses==192);
        assert(receipt.fallback_blocks==16);
    }
    const int w=985,h=124;
    uint32_t *screen=(uint32_t *)calloc((size_t)w*h,sizeof(uint32_t));
    assert(screen);
    assert(foj_budget_probe_draw(&receipt,screen,w,h,w));
    assert(screen[FOJ_BUDGET_Y*w+FOJ_BUDGET_STATUS_X]==UINT32_C(0xff54e394));
    assert(foj_budget_probe_draw(&receipt,screen,
                                FOJ_BUDGET_STATUS_X+8,FOJ_BUDGET_Y+8,w));
    assert(!foj_budget_probe_draw(&receipt,screen,
                                 FOJ_BUDGET_STATUS_X+7,h,w));
    assert(!foj_budget_probe_draw(&receipt,screen,w,FOJ_BUDGET_Y+7,w));
    assert(!foj_budget_probe_draw(&receipt,screen,w,h,w-1));
    receipt.passed=false;
    assert(foj_budget_probe_draw(&receipt,screen,w,h,w));
    assert(screen[FOJ_BUDGET_Y*w+FOJ_BUDGET_STATUS_X]==UINT32_C(0xff2929f4));
    free(screen);free(a);free(b);
}
int main(void) {test_384_frame_receipt();return 0;}
