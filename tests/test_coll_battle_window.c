/* Stage218: generated-only raw COLL window, never a gameplay collision rule. */
#include "coll_battle_window.h"

#include <assert.h>
#include <math.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

static FojCollGrid source;
static FojCollBattleWindow window;

static void synthetic_grid(void) {
    memset(&source, 0, sizeof(source));
    source.width = 50;
    source.height = 50;
    for (int y=0;y<50;++y)
        for (int x=0;x<50;++x) {
            for (unsigned n=0;n<4;++n)
                source.samples[y][x][n] =
                    (float)(x*3+y*7+(int)n)*0.25f;
            source.flags[y][x][0] = (uint8_t)((x+y)%2);
            source.flags[y][x][1] = (uint8_t)((x+2*y)%3==0);
        }
}

static void test_exact_window_preserves_channels(void) {
    synthetic_grid();
    assert(foj_coll_battle_window(&source,21,22,&window));
    assert(window.source_x==21 && window.source_y==22);
    assert(window.source_width==50 && window.source_height==50);
    float sample = -1.0f;
    uint8_t flag=255;
    for (int y=0;y<FOJ_HEIGHT;++y)
        for (int x=0;x<FOJ_WIDTH;++x) {
            for (unsigned n=0;n<4;++n) {
                assert(foj_coll_window_sample(&window,x,y,n,&sample));
                assert(sample == source.samples[22+y][21+x][n]);
            }
            for (unsigned n=0;n<2;++n) {
                assert(foj_coll_window_flag(&window,x,y,n,&flag));
                assert(flag==source.flags[22+y][21+x][n]);
            }
        }
}

static void test_reject_bounds_and_zero_result(void) {
    synthetic_grid();
    memset(&window, 0xAB, sizeof(window));
    assert(!foj_coll_battle_window(&source,-1,22,&window));
    assert(window.source_width==0);
    assert(!foj_coll_window_sample(&window,0,0,0,
                                   &source.samples[0][0][0]));
    assert(!foj_coll_battle_window(&source,43,22,&window));
    assert(!foj_coll_battle_window(&source,21,45,&window));
    source.width=FOJ_WIDTH-1;
    assert(!foj_coll_battle_window(&source,0,0,&window));
    source.width=50;
    source.height=FOJ_HEIGHT-1;
    assert(!foj_coll_battle_window(&source,0,0,&window));
    source.height=50;
    assert(!foj_coll_battle_window(NULL,0,0,&window));
    assert(!foj_coll_battle_window(&source,0,0,NULL));
}

static void test_reject_nonfinite_and_corrupt_flags(void) {
    synthetic_grid();
    source.samples[22][21][1]=NAN;
    assert(!foj_coll_battle_window(&source,21,22,&window));
    assert(window.source_width==0);
    source.samples[22][21][1]=INFINITY;
    assert(!foj_coll_battle_window(&source,21,22,&window));
    source.samples[22][21][1]=4;
    source.flags[27][28][1]=2;
    assert(!foj_coll_battle_window(&source,21,22,&window));
    source.flags[27][28][1]=1;
    assert(foj_coll_battle_window(&source,21,22,&window));
}

static void test_read_boundaries_and_no_mutation_of_tactics(void) {
    synthetic_grid();
    assert(foj_coll_battle_window(&source,21,22,&window));
    float sample=1234;
    uint8_t flag=99;
    assert(!foj_coll_window_sample(&window,-1,0,0,&sample));
    assert(!foj_coll_window_sample(&window,8,0,0,&sample));
    assert(!foj_coll_window_sample(&window,0,6,0,&sample));
    assert(!foj_coll_window_sample(&window,0,0,4,&sample));
    assert(!foj_coll_window_sample(NULL,0,0,0,&sample));
    assert(!foj_coll_window_sample(&window,0,0,0,NULL));
    assert(!foj_coll_window_flag(&window,0,0,2,&flag));
    assert(!foj_coll_window_flag(&window,-1,0,0,&flag));
    assert(!foj_coll_window_flag(&window,0,0,0,NULL));
    assert(sample==1234 && flag==99);
    FojDemo map, prior;
    foj_demo_init(&map);
    prior=map;
    /* The bridge has no FojDemo parameter, no ability to alter game rules. */
    assert(foj_coll_battle_window(&source,21,22,&window));
    assert(memcmp(&map,&prior,sizeof(map))==0);
}

static void test_small_valid_grid(void) {
    synthetic_grid();
    source.width=FOJ_WIDTH;
    source.height=FOJ_HEIGHT;
    assert(foj_coll_battle_window(&source,0,0,&window));
    assert(window.source_width==FOJ_WIDTH);
    assert(!foj_coll_battle_window(&source,1,0,&window));
}

int main(void) {
    test_exact_window_preserves_channels();
    test_reject_bounds_and_zero_result();
    test_reject_nonfinite_and_corrupt_flags();
    test_read_boundaries_and_no_mutation_of_tactics();
    test_small_valid_grid();
    puts("Stage218 synthetic COLL research-window tests passed");
    return 0;
}
