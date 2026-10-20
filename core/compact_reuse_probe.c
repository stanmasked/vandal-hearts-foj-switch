/* Stage254: 900-KiB retained floor for 320x180 and 640x360.
 * Opt-in-only comparison against Stage253 exact-sized cache policy.
 * Measures allocated raster payload, not process RSS or fragmentation. */
#include "compact_reuse_probe.h"
#include <limits.h>
#include <stddef.h>
#include <string.h>
#if !defined(FOJ_STAGE254_REUSE) || !FOJ_STAGE254_REUSE
#error "The Stage254 bounded reuse probe must be explicitly enabled"
#endif

bool foj_reuse_probe_run(FojReuseReceipt *out,
                         const FojCompactChurnReceipt *baseline,
                         uint32_t *cached,uint32_t *reference) {
    if(!out || !baseline || !baseline->passed || !cached || !reference ||
       cached==reference || baseline->steps!=FOJ_REUSE_FRAMES ||
       baseline->allocations!=48 || baseline->releases!=48 ||
       baseline->hits!=192 || baseline->misses!=192 ||
       baseline->peak_kib!=3600)return false;
    *out=(FojReuseReceipt){0};
    FojCompactBaseCache c={0};
    foj_compact_base_init(&c);
    c.reuse_floor_bytes=(size_t)FOJ_REUSE_FLOOR_KIB*1024u;
    static const int widths[3]={320,640,1280};
    static const int heights[3]={180,360,720};
    bool ok=true;
    uint16_t peak_kib=0;
    for(int n=0;n<FOJ_REUSE_FRAMES;++n) {
        const int block=n/FOJ_CHURN_BLOCK;
        const int mode=block%3;
        const int w=widths[mode],h=heights[mode];
        const int variant=(n%FOJ_CHURN_BLOCK)/2;
        const size_t used=(size_t)w*(size_t)h*sizeof(uint32_t);
        const size_t expected_capacity=mode==2 ? (size_t)3600*1024u :
                                       (size_t)FOJ_REUSE_FLOOR_KIB*1024u;
        const uint64_t before=c.allocations;
        FojDemo scene;
        foj_demo_init(&scene);
        scene.cursor_x=variant;
        scene.cursor_y=block%FOJ_HEIGHT;
        scene.cells[0][0].elevation=(uint8_t)variant;
        const int expected_result=n%2==0 ? 0:1;
        const bool expect_new=n%FOJ_CHURN_BLOCK==0 && mode!=1;
        if(foj_compact_base_draw(&c,&scene,cached,w,h,w)!=expected_result ||
           !c.valid || c.allocated_bytes!=expected_capacity ||
           c.allocations!=before+(expect_new?1u:0u)) {
            ok=false;break;
        }
        /* Reference renderer is independent of the cached destination. */
        foj_iso_render(&scene,reference,w,h,w);
        if(memcmp(cached,reference,used)!=0){ok=false;break;}
        const size_t capacity_kib=c.allocated_bytes/1024u;
        if(capacity_kib>peak_kib)peak_kib=(uint16_t)capacity_kib;
        ++out->frames;
    }
    foj_compact_base_release(&c);
    out->exact_allocations=baseline->allocations;
    out->reuse_allocations=(uint16_t)c.allocations;
    out->reuse_releases=(uint16_t)c.releases;
    out->allocations_saved=(uint16_t)(
        out->exact_allocations>=out->reuse_allocations ?
        out->exact_allocations-out->reuse_allocations : 0);
    out->extra_small_kib=FOJ_REUSE_FLOOR_KIB-225;
    out->passed=ok && out->frames==FOJ_REUSE_FRAMES &&
        out->reuse_allocations==32 && out->reuse_releases==32 &&
        out->allocations_saved==16 && out->extra_small_kib==675 &&
        c.hits==192 && c.misses==192 && c.bypasses==0 &&
        peak_kib==3600 && !c.raster && !c.valid && c.allocated_bytes==0;
    return out->passed;
}

bool foj_reuse_probe_draw(const FojReuseReceipt *out,
                          uint32_t *pixels,int width,int height,int stride) {
    if(!out || !pixels || width<FOJ_REUSE_STATUS_X+8 ||
       height<FOJ_REUSE_Y+8 || stride<width || stride<=0 ||
       height>INT_MAX/stride)return false;
    const uint16_t v[6]={out->frames,out->exact_allocations,
                         out->reuse_allocations,out->reuse_releases,
                         out->allocations_saved,out->extra_small_kib};
    const uint32_t on[6]={
        UINT32_C(0xff77d6a3),UINT32_C(0xffe5c475),
        UINT32_C(0xff6ac9e7),UINT32_C(0xffaf92e5),
        UINT32_C(0xffda94ae),UINT32_C(0xff9cc0ed)
    };
    const uint32_t off=UINT32_C(0xff302530);
    const uint32_t pending=UINT32_C(0xffb28c51);
    for(int i=0;i<6;++i)
        for(int bit=0;bit<16;++bit) {
            const int x=FOJ_REUSE_X+i*72+bit*4;
            const uint32_t color= !out->passed ? pending:
                (v[i]&(UINT16_C(1)<<bit)) ? on[i]:off;
            for(int y=0;y<8;++y)
                for(int d=0;d<3;++d)
                    pixels[(FOJ_REUSE_Y+y)*stride+x+d]=color;
        }
    const uint32_t tile=out->passed ? UINT32_C(0xff54e394) :
        UINT32_C(0xff2929f4);
    for(int y=0;y<8;++y)
        for(int d=0;d<8;++d)
            pixels[(FOJ_REUSE_Y+y)*stride+FOJ_REUSE_STATUS_X+d]=tile;
    return true;
}
