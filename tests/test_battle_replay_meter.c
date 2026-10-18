/* Generated-only Stage229 meter: rejects invalid canvases and tracks real input. */
#include "battle_replay_meter.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>

enum { W=384, H=20, STRIDE=389, SENTINEL=19 };
static uint32_t pixels[STRIDE*H+SENTINEL];
static const uint32_t GREEN=UINT32_C(0xffe5a139);
static const uint32_t EMPTY=UINT32_C(0xff393129);
static const uint32_t GUARD=UINT32_C(0x76543210);

static void fill(void) {
    for (size_t i=0;i<sizeof(pixels)/sizeof(pixels[0]);++i)
        pixels[i]=GUARD;
}

static void check_padding(void) {
    for(int y=0;y<H;++y)
        for(int x=W;x<STRIDE;++x)
            assert(pixels[y*STRIDE+x]==GUARD);
    for(size_t i=STRIDE*H;i<sizeof(pixels)/sizeof(pixels[0]);++i)
        assert(pixels[i]==GUARD);
}

static void assert_count(FojBattleReplay *log, unsigned count) {
    assert(foj_replay_render_meter(log,pixels,W,H,STRIDE));
    for(int y=FOJ_REPLAY_METER_Y;
        y<FOJ_REPLAY_METER_Y+FOJ_REPLAY_METER_HEIGHT;++y)
        for(int x=0;x<FOJ_REPLAY_MAX_INPUTS;++x)
            assert(pixels[y*STRIDE+FOJ_REPLAY_METER_X+x]==
                   (x<(int)count?GREEN:EMPTY));
    check_padding();
}

static void test_live_actions_move_bar(void) {
    FojBattleReplay log;
    FojBattle b;
    foj_replay_init(&log); foj_battle_init(&b); fill();
    assert_count(&log,0);
    assert(foj_replay_record(&log,&b,FOJ_REPLAY_A,NULL));
    assert(foj_replay_record(&log,&b,FOJ_REPLAY_RIGHT,NULL));
    assert(foj_replay_record(&log,&b,FOJ_REPLAY_RIGHT,NULL));
    assert(foj_replay_record(&log,&b,FOJ_REPLAY_A,NULL));
    assert_count(&log,4);
    assert(foj_replay_record(&log,&b,FOJ_REPLAY_B,NULL));
    assert_count(&log,5);
    assert(foj_replay_record(&log,&b,FOJ_REPLAY_A,NULL));
    assert(foj_replay_record(&log,&b,FOJ_REPLAY_RIGHT,NULL));
    assert(foj_replay_record(&log,&b,FOJ_REPLAY_A,NULL));
    assert_count(&log,8);
    assert(foj_replay_matches(&log,&b));
}

static void test_full_log_and_fail_closed_canvas(void) {
    FojBattleReplay log;
    foj_replay_init(&log);
    fill();
    log.count=FOJ_REPLAY_MAX_INPUTS;
    assert_count(&log,FOJ_REPLAY_MAX_INPUTS);
    log.count=FOJ_REPLAY_MAX_INPUTS+1;
    uint32_t snapshot[STRIDE*H+SENTINEL];
    memcpy(snapshot,pixels,sizeof(pixels));
    assert(!foj_replay_render_meter(&log,pixels,W,H,STRIDE));
    assert(!foj_replay_render_meter(NULL,pixels,W,H,STRIDE));
    assert(!foj_replay_render_meter(&log,NULL,W,H,STRIDE));
    log.count=1;
    assert(!foj_replay_render_meter(&log,pixels,W-1,H,STRIDE));
    assert(!foj_replay_render_meter(&log,pixels,W,H-1,STRIDE));
    assert(!foj_replay_render_meter(&log,pixels,W,H,W-1));
    assert(memcmp(snapshot,pixels,sizeof(pixels))==0);
}

int main(void) {
    test_live_actions_move_bar();
    test_full_log_and_fail_closed_canvas();
    puts("Stage229 replay input meter: two scenarios passed");
    return 0;
}
