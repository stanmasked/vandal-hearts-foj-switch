/* Stage244: genuine C11/UBSan controls for the SAME-PROCESS AB/BA probe.
 * No wall-clock assumptions, Switch SDK or original PS3 assets. */
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include "threat_pair_probe.h"

typedef struct {
    uint64_t ns;
    uint64_t step_ns;
} FakeClock;

static uint64_t next_tick(void *ctx) {
    FakeClock *clock=(FakeClock *)ctx;
    clock->ns+=clock->step_ns;
    return clock->ns;
}

static uint64_t frozen_tick(void *ctx) {
    (void)ctx;
    return 42u;
}

static void select_hero(FojBattle *battle) {
    foj_battle_init(battle);
    assert(foj_battle_confirm(battle) == FOJ_BATTLE_SELECTED);
    assert(battle->map.selected);
}

static void test_warm_equal_forecasts_32_pairs(void) {
    FojBattle battle, untouched;
    select_hero(&battle);
    untouched=battle;
    FojThreatPairProbe meter;
    foj_threat_pair_probe_init(&meter);
    FakeClock clock={0,1600};
    assert(!meter.ready && meter.parity_ok && !meter.failed);
    for (int n=0;n<FOJ_PAIR_PROBE_WINDOW;n++) {
        assert(foj_threat_pair_probe_step(&meter,&battle,next_tick,&clock));
        assert(meter.total_pairs==(unsigned)(n+1));
    }
    assert(!memcmp(&battle,&untouched,sizeof(battle)));
    assert(meter.ready && meter.parity_ok && !meter.failed);
    assert(meter.cached_mean_ns==100);
    assert(meter.uncached_mean_ns==100);
    assert(meter.completed_windows==1u);
    assert(meter.pair_count==0);
    assert(meter.experimental_cache.calculations==1u);
    assert(meter.experimental_cache.hits>=
           FOJ_PAIR_PROBE_WINDOW*(unsigned)FOJ_PAIR_PROBE_REPEATS);
    const unsigned previous=meter.total_pairs;
    foj_battle_move_cursor(&battle,1,0);
    assert(foj_threat_pair_probe_step(&meter,&battle,next_tick,&clock));
    assert(meter.total_pairs==previous+1u);
    assert(meter.experimental_cache.calculations==1u);
}

static void test_invalid_gameplay_and_key_invalidation(void) {
    FojBattle battle;
    select_hero(&battle);
    FojThreatPairProbe meter;
    foj_threat_pair_probe_init(&meter);
    FakeClock clock={0,1600};
    assert(foj_threat_pair_probe_step(&meter,&battle,next_tick,&clock));
    FojBattle invalid=battle;
    invalid.map.selected=false;
    assert(!foj_threat_pair_probe_step(&meter,&invalid,next_tick,&clock));
    assert(!meter.key_valid && !meter.ready && !meter.failed);
    assert(foj_threat_pair_probe_step(&meter,&battle,next_tick,&clock));
    assert(meter.total_pairs==1u);
    /* A change to the terrain must invalidate even a warm cache. */
    FojBattle varied=battle;
    varied.map.cells[0][0].elevation^=1;
    assert(foj_threat_pair_probe_step(&meter,&varied,next_tick,&clock));
    assert(meter.total_pairs==1u && meter.completed_windows==0u);
    assert(meter.experimental_cache.calculations==1u);
}

static void test_invalid_clock_fails_closed(void) {
    FojBattle battle;
    select_hero(&battle);
    FojThreatPairProbe meter;
    foj_threat_pair_probe_init(&meter);
    assert(!foj_threat_pair_probe_step(&meter,&battle,frozen_tick,NULL));
    assert(meter.failed && !meter.ready && !meter.parity_ok);
    assert(!foj_threat_pair_probe_step(&meter,&battle,frozen_tick,NULL));
    assert(!foj_threat_pair_probe_step(NULL,&battle,frozen_tick,NULL));
    assert(!foj_threat_pair_probe_step(&meter,&battle,NULL,NULL));
}

static void test_bounded_nanosecond_output(void) {
    FojBattle battle;
    select_hero(&battle);
    FojThreatPairProbe meter;
    foj_threat_pair_probe_init(&meter);
    FakeClock clock={0,1600};
    uint32_t pixels[768*24];
    for(unsigned n=0;n<sizeof(pixels)/sizeof(*pixels);n++)
        pixels[n]=UINT32_C(0xff123456);
    assert(foj_threat_pair_probe_draw(&meter,pixels,768,24,768));
    assert(pixels[12*768+FOJ_PAIR_PROBE_CACHED_X]==UINT32_C(0xffb8863f));
    for(int n=0;n<FOJ_PAIR_PROBE_WINDOW;n++)
        assert(foj_threat_pair_probe_step(&meter,&battle,next_tick,&clock));
    assert(foj_threat_pair_probe_draw(&meter,pixels,768,24,768));
    /* 100 decimal = 0x64, bits 2/5/6 set, bit 1 clear. */
    assert(pixels[12*768+FOJ_PAIR_PROBE_CACHED_X+8] ==
           UINT32_C(0xff33aa6f));
    assert(pixels[12*768+FOJ_PAIR_PROBE_UNCACHED_X+8] ==
           UINT32_C(0xffa36fe5));
    assert(pixels[12*768+FOJ_PAIR_PROBE_UNCACHED_X+4] ==
           UINT32_C(0xff302530));
    assert(pixels[12*768+FOJ_PAIR_PROBE_STATUS_X] ==
           UINT32_C(0xff33c956));
    assert(pixels[23*768+767] == UINT32_C(0xff123456));
    assert(!foj_threat_pair_probe_draw(&meter,pixels,759,24,768));
    assert(!foj_threat_pair_probe_draw(&meter,pixels,768,19,768));
    assert(!foj_threat_pair_probe_draw(&meter,pixels,768,24,767));
    assert(!foj_threat_pair_probe_draw(&meter,NULL,768,24,768));
    assert(!foj_threat_pair_probe_draw(NULL,pixels,768,24,768));
}

int main(void) {
    test_warm_equal_forecasts_32_pairs();
    test_invalid_gameplay_and_key_invalidation();
    test_invalid_clock_fails_closed();
    test_bounded_nanosecond_output();
    return EXIT_SUCCESS;
}
