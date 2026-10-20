/* Stage270: host-side test of the very same C11 native NRO preflight.
 * Synthetic clip-space triangles only. No deko3d SDK or proprietary data. */
#include "three_layer_preflight.h"
#include <math.h>
#include <stdio.h>
#include <stdint.h>
#include <string.h>

static unsigned checks=0;
#define CHECK(cond) do { ++checks; if (!(cond)) {     fprintf(stderr,"FAIL line %d: %s\n",__LINE__,#cond); return 1; } } while (0)

static const FojGpuBatch ORDERED[3]={
    {0,3,0},{3,3,1},{6,3,2}
};
static void put(FojGpuVertex *p,float x,float y,float z) {
    *p=(FojGpuVertex){x,y,z,1.f,0.f,0.f};
}
static void generated(FojGpuVertex *p) {
    const float near[3][2]={{-.76f,-.50f},{.34f,-.50f},{-.21f,.69f}};
    const float rear[3][2]={{-.35f,-.50f},{.75f,-.50f},{.20f,.69f}};
    for(unsigned k=0;k<3;++k) {
        put(p+k,near[k][0],near[k][1],.85f);
        put(p+k+3,near[k][0],near[k][1],.55f);
        put(p+k+6,rear[k][0],rear[k][1],.20f);
    }
}
int main(void) {
    FojGpuVertex v[9];generated(v);
    CHECK(foj_three_layer_preflight(v,9,ORDERED,3)==FOJ_THREE_ORDER_OK);
    CHECK(foj_three_layer_preflight(NULL,9,ORDERED,3)==FOJ_THREE_ORDER_INVALID);
    CHECK(foj_three_layer_preflight(v,9,NULL,3)==FOJ_THREE_ORDER_INVALID);
    CHECK(foj_three_layer_preflight(v,8,ORDERED,3)==FOJ_THREE_ORDER_INVALID);
    CHECK(foj_three_layer_preflight(v,9,ORDERED,2)==FOJ_THREE_ORDER_INVALID);

    FojGpuBatch bad[3];memcpy(bad,ORDERED,sizeof(bad));
    bad[1].texture_index=0;
    CHECK(foj_three_layer_preflight(v,9,bad,3)==FOJ_THREE_ORDER_INVALID);
    memcpy(bad,ORDERED,sizeof(bad));bad[1].first_vertex=4;
    CHECK(foj_three_layer_preflight(v,9,bad,3)==FOJ_THREE_ORDER_INVALID);

    generated(v);v[1].z=.40f;
    CHECK(foj_three_layer_preflight(v,9,ORDERED,3)==FOJ_THREE_ORDER_UNSAFE);
    generated(v);v[0].z=.40f;v[1].z=.95f;v[2].z=.65f;
    CHECK(foj_three_layer_preflight(v,9,ORDERED,3)==FOJ_THREE_ORDER_UNSAFE);
    generated(v);v[0].z=v[3].z;v[1].z=v[4].z;v[2].z=v[5].z;
    CHECK(foj_three_layer_preflight(v,9,ORDERED,3)==FOJ_THREE_ORDER_UNSAFE);
    generated(v);v[0].z=v[3].z+0.2e-6f;
    CHECK(foj_three_layer_preflight(v,9,ORDERED,3)==FOJ_THREE_ORDER_UNSAFE);
    generated(v);v[4].z=NAN;
    CHECK(foj_three_layer_preflight(v,9,ORDERED,3)==FOJ_THREE_ORDER_INVALID);
    generated(v);v[4].x=INFINITY;
    CHECK(foj_three_layer_preflight(v,9,ORDERED,3)==FOJ_THREE_ORDER_INVALID);
    generated(v);v[4].z=1.1f;
    CHECK(foj_three_layer_preflight(v,9,ORDERED,3)==FOJ_THREE_ORDER_INVALID);
    generated(v);v[4].w=.5f;
    CHECK(foj_three_layer_preflight(v,9,ORDERED,3)==FOJ_THREE_ORDER_INVALID);
    generated(v);v[4].x=2.f;
    CHECK(foj_three_layer_preflight(v,9,ORDERED,3)==FOJ_THREE_ORDER_INVALID);

    generated(v);
    /* Identical projected winding reversal must not change depth proof. */
    for(unsigned batch=0;batch<3;++batch) {
        const unsigned index=batch*3;
        FojGpuVertex tmp=v[index];
        v[index]=v[index+2];v[index+2]=tmp;
    }
    CHECK(foj_three_layer_preflight(v,9,ORDERED,3)==FOJ_THREE_ORDER_OK);

    generated(v);
    for(unsigned k=0;k<3;++k) {
        put(v+k,-.9f+.08f*k,-.9f+.08f*(k==2),.99f);
    }
    CHECK(foj_three_layer_preflight(v,9,ORDERED,3)==FOJ_THREE_ORDER_OK);

    generated(v);
    v[0].x=v[1].x;v[0].y=v[1].y;
    CHECK(foj_three_layer_preflight(v,9,ORDERED,3)==FOJ_THREE_ORDER_INVALID);

    fprintf(stdout,"Stage270 native C geometry preflight: %u cases passed\n",checks);
    return 0;
}
