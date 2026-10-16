/* No Switch binaries or original game data: portable GPU setup test. */
#include "smoke_plan.h"
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <math.h>

static void test_image_alignment(void) {
    uint32_t bytes=777;
    assert(foj_smoke_image_allocation(1280u*720u*4u,256,4096,&bytes));
    assert(bytes>=1280u*720u*4u);
    assert(!(bytes%4096u));
    assert(foj_smoke_image_allocation(4096,8192,4096,&bytes)&&bytes==8192);
    assert(!foj_smoke_image_allocation(1,3,4096,&bytes)&&bytes==8192);
    assert(!foj_smoke_image_allocation(UINT64_MAX,4096,4096,&bytes));
    assert(!foj_smoke_image_allocation(UINT32_MAX,4096,4096,&bytes));
    assert(!foj_smoke_image_allocation(0,4096,4096,&bytes));
    assert(!foj_smoke_image_allocation(1,4096,0,&bytes));
    assert(!foj_smoke_image_allocation(1,4096,4096,NULL));
    assert(bytes==8192);
}

static void test_vertex_buffer_alignment(void) {
    /* Three invented FojGpuVertex entries, each 6 x float32 = 24 bytes. */
    uint32_t bytes=0;
    assert(foj_smoke_image_allocation(3u*24u,4096,4096,&bytes));
    assert(bytes==4096u);

    /* Same layout for real model uploads; no original vertices included. */
    assert(foj_smoke_image_allocation(9066u*24u,4096,4096,&bytes));
    assert(bytes==221184u);
    assert(foj_smoke_image_allocation(20000u*24u,4096,4096,&bytes));
    assert(bytes==483328u);
}

static void test_palette(void) {
    float c[4]={0};
    assert(foj_smoke_color(0,c));
    assert(fabsf(c[0]-.21f)<1e-6f && fabsf(c[1]-.12f)<1e-6f);
    assert(c[3]==1.f);
    assert(foj_smoke_color(1,c));
    assert(fabsf(c[0]-.44f)<1e-6f && fabsf(c[1]-.57f)<1e-6f);
    assert(fabsf(c[2]-.43f)<1e-6f);
    assert(!foj_smoke_color(2,c));
    assert(fabsf(c[0]-.44f)<1e-6f);
    assert(!foj_smoke_color(0,NULL));
    assert(foj_smoke_color_for_frame(0)==0);
    assert(foj_smoke_color_for_frame(119)==0);
    assert(foj_smoke_color_for_frame(120)==1);
    assert(foj_smoke_color_for_frame(239)==1);
    assert(foj_smoke_color_for_frame(240)==0);
    assert(foj_smoke_color_for_frame(UINT64_MAX)<=1);
}

int main(void) {
    test_image_alignment();
    test_vertex_buffer_alignment();
    test_palette();
    puts("GPU smoke allocation and alternating-color plan: passed");
    return 0;
}
