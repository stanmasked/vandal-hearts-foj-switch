#ifndef FOJ_ISOMETRIC_DEMO_H
#define FOJ_ISOMETRIC_DEMO_H

/* Portable CPU rasterizer for generated isometric height-map research.
 * Not a PS3 renderer, 3D-model loader, or original FoJ asset decoder. */
#include <stdint.h>
#include "tactical_demo.h"
#include "tactical_battle.h"

void foj_iso_project(int width, int height, int x, int y, int elevation,
                     int *screen_x, int *screen_y);
void foj_iso_render(const FojDemo *state, uint32_t *pixels,
                    int width, int height, int stride_pixels);
/* Same synthetic terrain, plus HP bars and battle-result strip. */
void foj_iso_render_battle(const FojBattle *battle, uint32_t *pixels,
                           int width, int height, int stride_pixels);
/* Same battle result and damage visuals, but optional movement-risk hint.
 * This presentation option must never change FojBattle or replay history. */
void foj_iso_render_battle_options(const FojBattle *battle, uint32_t *pixels,
                                   int width, int height, int stride_pixels,
                                   bool show_threat_preview);

/* Optional cached rendering path used by the native isometric guest.
 * NULL cache retains the previous behavior; render output is identical. */
void foj_iso_render_battle_cached_options(const FojBattle *battle,
                                          uint32_t *pixels,
                                          int width, int height,
                                          int stride_pixels,
                                          bool show_threat_preview,
                                          FojBattleThreatCache *cache);


/* Stage246 research-only exclusive CPU phase timings. Callback is
 * monotonic nanoseconds; the production API below is left unchanged. */
typedef uint64_t (*FojIsoPhaseClockNs)(void *);
typedef struct {
    uint64_t terrain_ns;          /* 8x6 terrain + tokens + route */
    uint64_t threat_compute_ns;   /* risk-matrix cache lookup/recompute */
    uint64_t threat_paint_ns;     /* danger/landing markers */
    uint64_t battle_hud_ns;       /* health, guard, attack, enemy indicators */
    uint64_t whole_raster_ns;     /* sum of these exclusive stages */
    bool forecast_available;
    bool valid;
} FojIsoPhaseReceipt;

void foj_iso_render_battle_profiled(const FojBattle *battle,
                                    uint32_t *pixels,
                                    int width, int height,
                                    int stride_pixels,
                                    bool show_threat_preview,
                                    FojBattleThreatCache *cache,
                                    FojIsoPhaseClockNs clock_ns,
                                    void *clock_context,
                                    FojIsoPhaseReceipt *receipt);

#endif
