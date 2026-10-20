/* Stage255 generated-only, exactly-budgeted 384-frame guest proof.
 * No native FoJ engine, proprietary art or physical Switch memory metric. */
#include "compact_budget_probe.h"
#include <limits.h>
#include <stddef.h>
#include <string.h>
#if !defined(FOJ_STAGE255_BUDGET_FALLBACK) || !FOJ_STAGE255_BUDGET_FALLBACK || \
    !defined(FOJ_STAGE254_REUSE) || !FOJ_STAGE254_REUSE
#error "Stage255 optical probe requires both opt-in cache policies"
#endif

bool foj_budget_probe_run(FojBudgetReceipt *out,
                          uint32_t *cached,uint32_t *reference) {
    if(!out || !cached || !reference || cached==reference)return false;
    *out=(FojBudgetReceipt){0};
    FojCompactBaseCache c={0};
    foj_compact_base_init(&c);
    c.reuse_floor_bytes=(size_t)900u*1024u;
    static const int widths[3]={320,640,1280};
    static const int heights[3]={180,360,720};
    bool ok=true;
    for(int n=0;n<FOJ_BUDGET_FRAMES;++n) {
        const int block=n/FOJ_CHURN_BLOCK,mode=block%3;
        const int w=widths[mode],h=heights[mode];
        const int variant=(n%FOJ_CHURN_BLOCK)/2;
        const size_t bytes=(size_t)w*(size_t)h*sizeof(uint32_t);
        const uint64_t before=c.allocations;
        c.budget_bytes=bytes;
        FojDemo scene;
        foj_demo_init(&scene);
        scene.cursor_x=variant;
        scene.cursor_y=block%FOJ_HEIGHT;
        scene.cells[0][0].elevation=(uint8_t)variant;
        const int expected=n%2==0?0:1;
        if(foj_compact_base_draw(&c,&scene,cached,w,h,w)!=expected ||
           !c.valid || c.allocated_bytes!=bytes ||
           c.allocations!=before+(n%FOJ_CHURN_BLOCK==0?1u:0u)) {
            ok=false;break;
        }
        foj_iso_render(&scene,reference,w,h,w);
        if(memcmp(cached,reference,bytes)!=0){ok=false;break;}
        if(n%FOJ_CHURN_BLOCK==0 && mode==0)++out->fallback_blocks;
        if(expected==0)++out->misses;
        else ++out->hits;
        ++out->frames;
    }
    foj_compact_base_release(&c);
    out->allocations=(uint16_t)c.allocations;
    out->releases=(uint16_t)c.releases;
    out->passed=ok && out->frames==384 &&
        out->allocations==48 && out->releases==48 &&
        out->hits==192 && out->misses==192 &&
        out->fallback_blocks==16 &&
        c.hits==192 && c.misses==192 && c.bypasses==0 &&
        !c.raster && !c.valid && c.allocated_bytes==0;
    return out->passed;
}

bool foj_budget_probe_draw(const FojBudgetReceipt *out,
                           uint32_t *pixels,int width,int height,int stride) {
    if(!out || !pixels || width<FOJ_BUDGET_STATUS_X+8 ||
       height<FOJ_BUDGET_Y+8 || stride<width || stride<=0 ||
       height>INT_MAX/stride)return false;
    const uint16_t v[6]={out->frames,out->allocations,out->releases,
                         out->hits,out->misses,out->fallback_blocks};
    const uint32_t on[6]={
        UINT32_C(0xff77d6a3),UINT32_C(0xffe5c475),
        UINT32_C(0xff6ac9e7),UINT32_C(0xffaf92e5),
        UINT32_C(0xffda94ae),UINT32_C(0xff9cc0ed)
    };
    const uint32_t off=UINT32_C(0xff302530);
    const uint32_t pending=UINT32_C(0xffb28c51);
    for(int i=0;i<6;++i)
        for(int bit=0;bit<16;++bit) {
            const int x=FOJ_BUDGET_X+i*72+bit*4;
            const uint32_t color=!out->passed? pending:
                (v[i]&(UINT16_C(1)<<bit))?on[i]:off;
            for(int y=0;y<8;++y)
                for(int d=0;d<3;++d)
                    pixels[(FOJ_BUDGET_Y+y)*stride+x+d]=color;
        }
    const uint32_t tile=out->passed ? UINT32_C(0xff54e394):
        UINT32_C(0xff2929f4);
    for(int y=0;y<8;++y)
        for(int d=0;d<8;++d)
            pixels[(FOJ_BUDGET_Y+y)*stride+FOJ_BUDGET_STATUS_X+d]=tile;
    return true;
}
