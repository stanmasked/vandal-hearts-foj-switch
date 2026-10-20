/* Stage253: 384 frames, 48 size changes, 192 hits and 192 misses. */
#include "compact_churn_probe.h"
#include <assert.h>
#include <stdlib.h>
#include <stdint.h>
enum {MAXPIX=1280*720};
static uint32_t *fresh(void) {
    uint32_t *p=(uint32_t *)calloc(MAXPIX,sizeof(uint32_t));
    assert(p);return p;
}
static void test_endurance(void) {
    uint32_t *a=fresh(),*b=fresh();
    FojCompactChurnReceipt x={0};
    assert(!foj_compact_churn_run(NULL,a,b));
    assert(!foj_compact_churn_run(&x,NULL,b));
    assert(!foj_compact_churn_run(&x,a,a));
    for(int rep=0;rep<3;++rep) {
        assert(foj_compact_churn_run(&x,a,b));
        assert(x.passed && x.steps==384 && x.allocations==48);
        assert(x.releases==48 && x.hits==192 && x.misses==192);
        assert(x.peak_kib==3600);
    }
    /* No out-of-bounds telemetry pixels on the exact accepted edges. */
    const int width=985,height=88;
    uint32_t *screen=(uint32_t *)calloc((size_t)width*height,sizeof(uint32_t));
    assert(screen);
    assert(foj_compact_churn_draw(&x,screen,width,height,width));
    assert(screen[FOJ_CHURN_Y*width+FOJ_CHURN_STATUS_X]==
           UINT32_C(0xff54e394));
    assert(foj_compact_churn_draw(&x,screen,FOJ_CHURN_STATUS_X+8,
                                  FOJ_CHURN_Y+8,width));
    assert(!foj_compact_churn_draw(&x,screen,FOJ_CHURN_STATUS_X+7,
                                   height,width));
    assert(!foj_compact_churn_draw(&x,screen,width,FOJ_CHURN_Y+7,width));
    assert(!foj_compact_churn_draw(&x,screen,width,height,width-1));
    x.passed=false;
    assert(foj_compact_churn_draw(&x,screen,width,height,width));
    assert(screen[FOJ_CHURN_Y*width+FOJ_CHURN_STATUS_X]==
           UINT32_C(0xff2929f4));
    free(screen);free(a);free(b);
}
int main(void){test_endurance();return 0;}
