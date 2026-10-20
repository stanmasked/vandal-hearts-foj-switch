#ifndef FOJ_BASE_CACHE_COMPACT_H
#define FOJ_BASE_CACHE_COMPACT_H
/* Stage251 opt-in, generated-only CPU scene cache with exact-sized heap
 * pixel storage. No original PS3 assets, GPU memory or frame presentation. */
#include "isometric_demo.h"
#include <stddef.h>
#include <stdint.h>
#include <stdbool.h>

typedef struct {
    uint32_t *raster;
    size_t allocated_bytes; /* requested pixel payload, not allocator RSS */
    size_t budget_bytes;
    FojDemo scene;
    int width, height;
    uint64_t hits, misses, bypasses, allocations, releases;
    bool valid;
#if defined(FOJ_STAGE252_STRESS) && FOJ_STAGE252_STRESS
    /* Research-only deterministic allocator failure; default build omits. */
    bool inject_fail_next_allocation;
#endif
} FojCompactBaseCache;

/* Init only a zero-initialized or already released struct. */
void foj_compact_base_init(FojCompactBaseCache *cache);
/* Release heap storage; preserve no cache validity. */
void foj_compact_base_release(FojCompactBaseCache *cache);
/* Release and reset counters for a new scene-level sweep. */
void foj_compact_base_reset(FojCompactBaseCache *cache);
/* -1 = invalid or allocation failed; 0 = cold render; 1 = warm cache hit.
 * In both valid cases the active pixel region is filled. Padding untouched.
 * On memory failure never claim a valid hit or re-use stale pixel storage. */
int foj_compact_base_draw(FojCompactBaseCache *cache,const FojDemo *scene,
                          uint32_t *pixels,int width,int height,int stride);
#endif
