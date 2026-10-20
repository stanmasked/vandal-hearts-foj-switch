#include "base_cache_compact.h"
#include <limits.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
/* Stage255 is opt-in and requires the Stage254 capacity policy. */
#if defined(FOJ_STAGE255_BUDGET_FALLBACK) && FOJ_STAGE255_BUDGET_FALLBACK && \
    (!defined(FOJ_STAGE254_REUSE) || !FOJ_STAGE254_REUSE)
#error "Stage255 budget fallback requires FOJ_STAGE254_REUSE=1"
#endif

static bool same_scene(const FojDemo *a,const FojDemo *b) {
    if(a->hero_x!=b->hero_x || a->hero_y!=b->hero_y ||
       a->enemy_x!=b->enemy_x || a->enemy_y!=b->enemy_y ||
       a->cursor_x!=b->cursor_x || a->cursor_y!=b->cursor_y ||
       a->selected!=b->selected)return false;
    for(int y=0;y<FOJ_HEIGHT;++y)
        for(int x=0;x<FOJ_WIDTH;++x)
            if(a->cells[y][x].elevation!=b->cells[y][x].elevation ||
               a->cells[y][x].blocked!=b->cells[y][x].blocked)
                return false;
    return true;
}
void foj_compact_base_init(FojCompactBaseCache *p) {
    if(!p)return;
    p->raster=NULL;p->allocated_bytes=0;
    p->budget_bytes=(size_t)FOJ_ISO_BASE_CACHE_WIDTH*
                    FOJ_ISO_BASE_CACHE_HEIGHT*sizeof(uint32_t);
    p->width=p->height=0;p->valid=false;
    p->hits=p->misses=p->bypasses=p->allocations=p->releases=0;
#if defined(FOJ_STAGE254_REUSE) && FOJ_STAGE254_REUSE
    p->reuse_floor_bytes=0;
#endif
#if defined(FOJ_STAGE252_STRESS) && FOJ_STAGE252_STRESS
    p->inject_fail_next_allocation=false;
#endif
}
void foj_compact_base_release(FojCompactBaseCache *p) {
    if(!p)return;
    if(p->raster) {
        free(p->raster);
        p->raster=NULL;
        if(p->releases!=UINT64_MAX)++p->releases;
    }
    p->allocated_bytes=0;p->width=p->height=0;p->valid=false;
}
void foj_compact_base_reset(FojCompactBaseCache *p) {
    if(!p)return;
    foj_compact_base_release(p);
    p->hits=p->misses=p->bypasses=p->allocations=p->releases=0;
}
static void increment(uint64_t *v) {
    if(*v!=UINT64_MAX)++*v;
}
int foj_compact_base_draw(FojCompactBaseCache *p,const FojDemo *scene,
                          uint32_t *pixels,int width,int height,int stride) {
    if(!p || !scene || !pixels || width<=0 || height<=0 ||
       width>FOJ_ISO_BASE_CACHE_WIDTH ||
       height>FOJ_ISO_BASE_CACHE_HEIGHT || stride<width ||
       height>INT_MAX/stride)return -1;
    const size_t row=(size_t)width*sizeof(uint32_t);
    const size_t used=row*(size_t)height;
#if defined(FOJ_STAGE254_REUSE) && FOJ_STAGE254_REUSE
    /* Alternative capacity policy is strictly gated to Stage254 builds.
     * Only actual pixel payload is used; spare capacity is never pixels. */
    size_t target = used < p->reuse_floor_bytes ?
                    p->reuse_floor_bytes : used;
#if defined(FOJ_STAGE255_BUDGET_FALLBACK) && FOJ_STAGE255_BUDGET_FALLBACK
    /* A budget below the reuse floor must not reject a smaller frame
     * that fits exactly. No partial frame or over-budget allocation.
     * A lowered budget also invalidates any old oversized reservation. */
    if(target>p->budget_bytes && used<=p->budget_bytes)
        target=used;
    if(target>p->budget_bytes) {
        foj_compact_base_release(p);
        return -1;
    }
#else
    if(target>p->budget_bytes)return -1;
#endif
#else
    const size_t target=used;
    if(used>p->budget_bytes)return -1;
#endif
    if(p->valid && p->raster && p->allocated_bytes==target &&
       p->width==width && p->height==height &&
       same_scene(&p->scene,scene)) {
        for(int y=0;y<height;++y)
            memcpy(pixels+(size_t)y*(size_t)stride,
                   p->raster+(size_t)y*(size_t)width,row);
        increment(&p->hits);
        return 1;
    }
    /* Release before replacement: no simultaneous old+new cache payload
     * and no hidden max-size reservation when rendering a smaller frame. */
    if(p->allocated_bytes!=target || !p->raster) {
        foj_compact_base_release(p);
#if defined(FOJ_STAGE252_STRESS) && FOJ_STAGE252_STRESS
        /* Deterministic fault occurs only at a genuine allocation site;
         * the old block is already freed and cannot be reused stale. */
        if(p->inject_fail_next_allocation) {
            p->inject_fail_next_allocation=false;
            p->valid=false;
            return -1;
        }
#endif
        p->raster=(uint32_t *)malloc(target);
        if(!p->raster) {p->valid=false;return -1;}
        p->allocated_bytes=target;
        increment(&p->allocations);
    }
    p->valid=false;
    foj_iso_render(scene,pixels,width,height,stride);
    for(int y=0;y<height;++y)
        memcpy(p->raster+(size_t)y*(size_t)width,
               pixels+(size_t)y*(size_t)stride,row);
    p->scene=*scene;p->width=width;p->height=height;p->valid=true;
    increment(&p->misses);
    return 0;
}
