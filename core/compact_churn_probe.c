/* Opt-in, generated-only 384-frame allocation churn trace.
 * This is an accounting test, NOT an allocator fragmentation/RSS probe. */
#include "compact_churn_probe.h"
#include <limits.h>
#include <stddef.h>
#include <string.h>
#if !defined(FOJ_STAGE253_CHURN) || !FOJ_STAGE253_CHURN
#error "Stage253 churn requires explicit opt-in"
#endif

bool foj_compact_churn_run(FojCompactChurnReceipt *out,
                           uint32_t *cached,uint32_t *reference) {
    if(!out || !cached || !reference || cached==reference)return false;
    *out=(FojCompactChurnReceipt){0};
    FojCompactBaseCache c={0};
    foj_compact_base_init(&c);
    static const int widths[3]={320,640,1280};
    static const int heights[3]={180,360,720};
    bool ok=true;
    for(int n=0;n<FOJ_CHURN_STEPS;++n) {
        const int block=n/FOJ_CHURN_BLOCK;
        const int mode=block%3;
        const int w=widths[mode],h=heights[mode];
        const int variant=(n%FOJ_CHURN_BLOCK)/2;
        const size_t bytes=(size_t)w*(size_t)h*sizeof(uint32_t);
        const uint64_t alloc_before=c.allocations;
        FojDemo s;
        foj_demo_init(&s);
        s.cursor_x=variant;
        s.cursor_y=block%FOJ_HEIGHT;
        s.cells[0][0].elevation=(uint8_t)variant;
        const int expected=(n%2==0)?0:1;
        if(foj_compact_base_draw(&c,&s,cached,w,h,w)!=expected ||
           c.allocated_bytes!=bytes || !c.valid ||
           c.allocations!=alloc_before+(n%FOJ_CHURN_BLOCK==0?1u:0u)) {
            ok=false;break;
        }
        /* Every frame receives a fresh, uncached reference render. */
        foj_iso_render(&s,reference,w,h,w);
        if(memcmp(cached,reference,bytes)!=0){ok=false;break;}
        if(expected==0)++out->misses;
        else ++out->hits;
        ++out->steps;
        const size_t used_kib=bytes/1024u;
        if(used_kib>out->peak_kib)out->peak_kib=(uint16_t)used_kib;
    }
    foj_compact_base_release(&c);
    out->allocations=(uint16_t)c.allocations;
    out->releases=(uint16_t)c.releases;
    out->passed=ok && out->steps==FOJ_CHURN_STEPS &&
        out->allocations==FOJ_CHURN_STEPS/FOJ_CHURN_BLOCK &&
        out->releases==out->allocations &&
        out->hits==FOJ_CHURN_STEPS/2 &&
        out->misses==FOJ_CHURN_STEPS/2 &&
        out->peak_kib==3600 &&
        c.hits==out->hits && c.misses==out->misses &&
        c.bypasses==0 && !c.raster && !c.valid && c.allocated_bytes==0;
    return out->passed;
}

bool foj_compact_churn_draw(const FojCompactChurnReceipt *out,
                            uint32_t *pixels,int width,int height,int stride) {
    if(!out || !pixels || width<FOJ_CHURN_STATUS_X+8 ||
       height<FOJ_CHURN_Y+8 || stride<width || stride<=0 ||
       height>INT_MAX/stride)return false;
    const uint16_t v[6]={out->steps,out->allocations,out->releases,
                         out->hits,out->misses,out->peak_kib};
    const uint32_t on[6]={
        UINT32_C(0xff58df95),UINT32_C(0xffdfb45c),
        UINT32_C(0xff8ea7ee),UINT32_C(0xff67d2e8),
        UINT32_C(0xffd77ac6),UINT32_C(0xffdcb1f2)
    };
    const uint32_t off=UINT32_C(0xff302530);
    const uint32_t pending=UINT32_C(0xffb28c51);
    for(int i=0;i<6;++i)
        for(int bit=0;bit<16;++bit) {
            const int x=FOJ_CHURN_X+i*72+bit*4;
            const uint32_t color=!out->passed ? pending :
                (v[i]&(UINT16_C(1)<<bit)) ? on[i]:off;
            for(int y=0;y<8;++y)
                for(int d=0;d<3;++d)
                    pixels[(FOJ_CHURN_Y+y)*stride+x+d]=color;
        }
    const uint32_t tile=out->passed ? UINT32_C(0xff54e394) :
        UINT32_C(0xff2929f4);
    for(int y=0;y<8;++y)
        for(int d=0;d<8;++d)
            pixels[(FOJ_CHURN_Y+y)*stride+FOJ_CHURN_STATUS_X+d]=tile;
    return true;
}
