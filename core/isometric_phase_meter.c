#include "isometric_phase_meter.h"
#include <limits.h>
#include <stddef.h>
#include <string.h>

void foj_iso_phase_meter_init(FojIsoPhaseMeter *meter) {
    if (meter) memset(meter,0,sizeof(*meter));
}

bool foj_iso_phase_meter_record(FojIsoPhaseMeter *meter,
                                const FojIsoPhaseReceipt *p) {
    if (!meter || !p || meter->failed) return false;
    if (!p->valid || !p->whole_raster_ns ||
        UINT64_MAX-meter->terrain_total_ns<p->terrain_ns ||
        UINT64_MAX-meter->forecast_total_ns<p->threat_compute_ns ||
        UINT64_MAX-meter->marker_total_ns<p->threat_paint_ns ||
        UINT64_MAX-meter->hud_total_ns<p->battle_hud_ns ||
        UINT64_MAX-meter->whole_total_ns<p->whole_raster_ns ||
        p->terrain_ns>UINT64_MAX-p->threat_compute_ns ||
        p->terrain_ns+p->threat_compute_ns>UINT64_MAX-p->threat_paint_ns ||
        p->terrain_ns+p->threat_compute_ns+p->threat_paint_ns>
            UINT64_MAX-p->battle_hud_ns ||
        p->terrain_ns+p->threat_compute_ns+p->threat_paint_ns+
            p->battle_hud_ns!=p->whole_raster_ns) {
        meter->failed=true;
        meter->ready=false;
        return false;
    }
    meter->terrain_total_ns+=p->terrain_ns;
    meter->forecast_total_ns+=p->threat_compute_ns;
    meter->marker_total_ns+=p->threat_paint_ns;
    meter->hud_total_ns+=p->battle_hud_ns;
    meter->whole_total_ns+=p->whole_raster_ns;
    meter->last_forecast_available=p->forecast_available;
    ++meter->frame_count;
    if (meter->frame_count==FOJ_PHASE_METER_WINDOW) {
        const uint64_t divisor=FOJ_PHASE_METER_WINDOW*UINT64_C(1000);
        const uint64_t values[5]={
            meter->terrain_total_ns/divisor,
            meter->forecast_total_ns/divisor,
            meter->marker_total_ns/divisor,
            meter->hud_total_ns/divisor,
            meter->whole_total_ns/divisor
        };
        if (!values[4]) {
            meter->failed=true;meter->ready=false;
            return false;
        }
        for (int i=0;i<5;++i) {
            if (values[i]>=65535) {
                meter->failed=true;meter->ready=false;
                return false;
            }
        }
        meter->terrain_mean_us=(uint16_t)values[0];
        meter->forecast_mean_us=(uint16_t)values[1];
        meter->markers_mean_us=(uint16_t)values[2];
        meter->hud_mean_us=(uint16_t)values[3];
        /* Every phase was measured with the same five clock ticks.
         * Rounding each phase separately can differ from total by <=3us. */
        const uint64_t sum=values[0]+values[1]+values[2]+values[3];
        if (sum>values[4] || values[4]-sum>3) {
            meter->failed=true;meter->ready=false;
            return false;
        }
        ++meter->completed_windows;
        meter->frame_count=0;
        meter->terrain_total_ns=0;
        meter->forecast_total_ns=0;
        meter->marker_total_ns=0;
        meter->hud_total_ns=0;
        meter->whole_total_ns=0;
        meter->ready=true;
    }
    return true;
}

bool foj_iso_phase_meter_draw(const FojIsoPhaseMeter *meter,
                              uint32_t *pixels, int width,
                              int height, int stride) {
    if (!meter || !pixels || width<FOJ_PHASE_METER_STATUS_X+8 ||
        height<FOJ_PHASE_METER_Y+8 || stride<width || stride<=0 ||
        height>INT_MAX/stride) return false;
    const int positions[4]={
        FOJ_PHASE_METER_TERRAIN_X,FOJ_PHASE_METER_FORECAST_X,
        FOJ_PHASE_METER_MARKERS_X,FOJ_PHASE_METER_HUD_X
    };
    /* libnx framebuffer: low-byte R, then G, B, alpha. */
    const uint32_t colors[4]={
        UINT32_C(0xff83d44a),UINT32_C(0xff4265eb),
        UINT32_C(0xff51bbde),UINT32_C(0xffef7f9a)
    };
    const uint32_t values[4]={
        meter->terrain_mean_us,meter->forecast_mean_us,
        meter->markers_mean_us,meter->hud_mean_us
    };
    const uint32_t pending=UINT32_C(0xffb8863f);
    const uint32_t off=UINT32_C(0xff302530);
    const uint32_t status=meter->failed?UINT32_C(0xff2222ff):
        meter->ready?UINT32_C(0xff84e65a):pending;
    for(int phase=0;phase<4;++phase) {
        for(int bit=0;bit<FOJ_PHASE_METER_BITS;++bit) {
            const int x=positions[phase]+bit*FOJ_PHASE_METER_STEP;
            const uint32_t shade=(!meter->ready||meter->failed)?pending:
                values[phase]&(UINT32_C(1)<<bit)?colors[phase]:off;
            for(int dy=0;dy<8;++dy)
                for(int dx=0;dx<3;++dx)
                    pixels[(FOJ_PHASE_METER_Y+dy)*stride+x+dx]=shade;
        }
    }
    for(int dy=0;dy<8;++dy)
        for(int dx=0;dx<8;++dx)
            pixels[(FOJ_PHASE_METER_Y+dy)*stride+
                   FOJ_PHASE_METER_STATUS_X+dx]=status;
    return true;
}
