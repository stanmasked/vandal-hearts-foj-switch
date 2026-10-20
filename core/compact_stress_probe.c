#include "compact_stress_probe.h"
#include <limits.h>
#include <stddef.h>
#include <string.h>

#if !defined(FOJ_STAGE252_STRESS) || !FOJ_STAGE252_STRESS
#error "The Stage252 compact stress module requires an explicit opt-in"
#endif

bool foj_compact_stress_run(FojCompactStressReceipt *out,
                            uint32_t *cached,uint32_t *reference) {
    if(!out || !cached || !reference || cached==reference)return false;
    *out=(FojCompactStressReceipt){0};
    FojCompactBaseCache c={0};
    foj_compact_base_init(&c);
    static const int widths[3]={320,640,1280};
    static const int heights[3]={180,360,720};
    bool ok=true;
    for(int i=0;i<FOJ_COMPACT_STRESS_ITERATIONS;++i) {
        const int w=widths[i%3],h=heights[i%3];
        const size_t payload=(size_t)w*(size_t)h*sizeof(uint32_t);
        FojDemo scene;
        foj_demo_init(&scene);
        scene.cursor_x=i%FOJ_WIDTH;
        scene.cursor_y=(i/FOJ_WIDTH)%FOJ_HEIGHT;
        scene.cells[0][0].elevation=(uint8_t)(i%4);
        if(i%FOJ_COMPACT_STRESS_FAULT_DIVISOR==0) {
            c.inject_fail_next_allocation=true;
            if(foj_compact_base_draw(&c,&scene,cached,w,h,w)!=-1 ||
               c.valid || c.raster || c.allocated_bytes!=0 ||
               c.inject_fail_next_allocation) {ok=false;break;}
            ++out->injected_failures;
        }
        if(foj_compact_base_draw(&c,&scene,cached,w,h,w)!=0 ||
           !c.valid || c.allocated_bytes!=payload) {ok=false;break;}
        if(foj_compact_base_draw(&c,&scene,reference,w,h,w)!=1 ||
           memcmp(cached,reference,payload)!=0) {ok=false;break;}
        /* Uncached reference is always outside the warm-cache copy. */
        foj_iso_render(&scene,reference,w,h,w);
        if(memcmp(cached,reference,payload)!=0) {ok=false;break;}
        ++out->cycles;
        if(payload/1024u>out->peak_kib)out->peak_kib=(uint16_t)(payload/1024u);
    }
    foj_compact_base_release(&c);
    out->allocations=(uint16_t)c.allocations;
    out->releases=(uint16_t)c.releases;
    out->passed=ok &&
        out->cycles==FOJ_COMPACT_STRESS_ITERATIONS &&
        out->injected_failures==8 &&
        out->allocations==FOJ_COMPACT_STRESS_ITERATIONS &&
        out->releases==FOJ_COMPACT_STRESS_ITERATIONS &&
        out->peak_kib==3600 &&
        c.hits==FOJ_COMPACT_STRESS_ITERATIONS &&
        c.misses==FOJ_COMPACT_STRESS_ITERATIONS &&
        !c.valid && !c.raster && c.allocated_bytes==0;
    return out->passed;
}
bool foj_compact_stress_draw(const FojCompactStressReceipt *out,
                             uint32_t *pixels,int width,int height,int stride) {
    if(!out || !pixels || width<FOJ_COMPACT_STRESS_STATUS_X+8 ||
       height<FOJ_COMPACT_STRESS_Y+8 || stride<width || stride<=0 ||
       height>INT_MAX/stride)return false;
    const uint16_t numbers[4]={
        out->cycles,out->injected_failures,out->allocations,out->peak_kib
    };
    const uint32_t on[4]={
        UINT32_C(0xff5cda8d),UINT32_C(0xffd59f6c),
        UINT32_C(0xff6ccdea),UINT32_C(0xffb971ef)
    };
    const uint32_t off=UINT32_C(0xff302530);
    const uint32_t pending=UINT32_C(0xffb28c51);
    for(int i=0;i<4;++i)
        for(int bit=0;bit<16;++bit) {
            const int x=FOJ_COMPACT_STRESS_FIRST_X+i*72+bit*4;
            const uint32_t color=!out->passed ? pending :
                (numbers[i]&(UINT16_C(1)<<bit)) ? on[i]:off;
            for(int y=0;y<8;++y)
                for(int d=0;d<3;++d)
                    pixels[(FOJ_COMPACT_STRESS_Y+y)*stride+x+d]=color;
        }
    const uint32_t tile=out->passed ? UINT32_C(0xff54e394) :
        UINT32_C(0xff2929f4);
    for(int y=0;y<8;++y)
        for(int d=0;d<8;++d)
            pixels[(FOJ_COMPACT_STRESS_Y+y)*stride+
                   FOJ_COMPACT_STRESS_STATUS_X+d]=tile;
    return true;
}
