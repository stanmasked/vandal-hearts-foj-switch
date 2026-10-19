#ifndef FOJ_ISOMETRIC_BASE_CACHE_H
#define FOJ_ISOMETRIC_BASE_CACHE_H

/* Stage247 experimental scene-validated framebuffer cache.
 * Generated-only 8x6 research terrain. No original PS3 data or GPU work.
 * ~3.52 MiB fixed pixel capacity; allocate statically or on heap,
 * never as a temporary on a small Switch thread stack. */
#include <stdbool.h>
#include <stdint.h>
#include "tactical_demo.h"

enum { FOJ_ISO_BASE_CACHE_WIDTH = 1280, FOJ_ISO_BASE_CACHE_HEIGHT = 720 };

typedef struct FojIsoBaseCache {
    uint32_t raster[FOJ_ISO_BASE_CACHE_WIDTH * FOJ_ISO_BASE_CACHE_HEIGHT];
    FojDemo scene;
    int width, height;
    uint64_t hits, misses, bypasses;
    bool valid;
} FojIsoBaseCache;

/* Init invalidates previous pixels; old memory need not be zeroed. */
void foj_iso_base_cache_init(FojIsoBaseCache *cache);

/* Renders exactly the same base terrain, tokens, cursor, route and selection
 * as foj_iso_render(). Returns true only when a scene-exact cached copy was
 * reused; cache misses still run the original renderer. Gameplay overlays
 * and forecast caches are processed independently, on every frame.
 * Unsupported dimensions bypass caching and draw normally.
 * Strided destination padding is never overwritten. */
bool foj_iso_base_cache_draw(FojIsoBaseCache *cache,
                             const FojDemo *scene, uint32_t *pixels,
                             int width, int height, int stride_pixels);

#endif
