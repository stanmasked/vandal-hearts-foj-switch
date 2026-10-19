#ifndef FOJ_STAGE245_RENDER_PAIR_H
#define FOJ_STAGE245_RENDER_PAIR_H
/* Asset-free software rasterizer benchmark: same guest process, identical
 * battle input, two distinct output buffers and AB/BA timing order.
 * This instrument NEVER supplies the visible game's render cache. */
#include "isometric_demo.h"
#include <stdbool.h>
#include <stdint.h>

enum {
    FOJ_RENDER_PAIR_WINDOW = 32,
    FOJ_RENDER_PAIR_BITS = 16,
    FOJ_RENDER_PAIR_BAR_STEP = 4,
    FOJ_RENDER_PAIR_CACHED_X = 780,
    FOJ_RENDER_PAIR_UNCACHED_X = 852,
    FOJ_RENDER_PAIR_STATUS_X = 924,
    FOJ_RENDER_PAIR_Y = 12,
    FOJ_RENDER_PAIR_MAX_US = 65535
};
typedef uint64_t (*FojRenderPairClockNs)(void *);
typedef struct {
    FojBattleThreatCache cache;
    FojBattle key;
    uint64_t cached_sum_ns;
    uint64_t uncached_sum_ns;
    uint32_t cached_mean_us;
    uint32_t uncached_mean_us;
    uint32_t samples;
    uint32_t total_pairs;
    uint32_t completed_windows;
    bool state_valid;
    bool show_threat_preview;
    bool ready;
    bool parity_ok;
    bool failed;
} FojRenderPairProbe;

void foj_render_pair_init(FojRenderPairProbe *meter);
/* Private buffers must be >= stride*height uint32_t each, disjoint, and
 * external to the main game framebuffer. Clock returns guest nanoseconds. */
bool foj_render_pair_step(FojRenderPairProbe *meter,
                          const FojBattle *battle, bool show_preview,
                          uint32_t *cached_pixels, uint32_t *uncached_pixels,
                          int width, int height, int stride,
                          FojRenderPairClockNs clock_ns, void *context);
/* Two 16-bit averages (microseconds per complete CPU rasterizer call)
 * and 8x8 audit tile; output rendered AFTER any timed calculations. */
bool foj_render_pair_draw(const FojRenderPairProbe *meter,
                          uint32_t *pixels, int width, int height, int stride);
#endif
