/* Stage269 generated-only native triangle sorting regression.
 * This is a host test of the C guard, not NeXium screenshots.
 */
#include "transparent_order_guard.h"
#include <math.h>
#include <stdio.h>
#include <string.h>

static int failures=0;
static void check(int condition,const char *label) {
    if (!condition) {
        fprintf(stderr,"FAIL: %s\n",label);
        ++failures;
    }
}
static FojGpuVertex vtx(float x,float y,float z) {
    FojGpuVertex v={x,y,z,1.f,0.f,0.f};
    return v;
}
static void scene(FojGpuVertex out[9],FojGpuBatch batches[3]) {
    const float ax[3]={-.76f,.34f,-.21f};
    const float ay[3]={-.50f,-.50f,.69f};
    const float cx[3]={-.35f,.75f,.20f};
    const float cy[3]={-.50f,-.50f,.69f};
    for (unsigned i=0;i<3u;++i) {
        out[i]=vtx(ax[i],ay[i],.85f);     /* near violet */
        out[3u+i]=vtx(ax[i],ay[i],.55f);  /* middle warm */
        out[6u+i]=vtx(cx[i],cy[i],.20f);  /* rear cool */
        batches[i]=(FojGpuBatch){3u*i,3u,i};
    }
}
static FojGpuOrderStatus assess(FojGpuVertex vertices[9],
                                 FojGpuBatch batches[3]) {
    return foj_gpu_three_layer_order_guard(vertices,9,batches,3);
}
int main(void) {
    FojGpuVertex vertices[9];
    FojGpuBatch batches[3];
    scene(vertices,batches);
    check(assess(vertices,batches)==FOJ_GPU_ORDER_OK,
          "Stage267 generated near/middle/rear triangles accepted");
    check(strcmp(foj_gpu_order_status_name(FOJ_GPU_ORDER_OK),
                 "safe fixed three-layer order")==0,
          "stable result name");
    check(foj_gpu_three_layer_order_guard(NULL,9,batches,3)==
          FOJ_GPU_ORDER_ARGUMENT,"null vertices rejected");
    check(foj_gpu_three_layer_order_guard(vertices,9,NULL,3)==
          FOJ_GPU_ORDER_ARGUMENT,"null batches rejected");
    check(foj_gpu_three_layer_order_guard(vertices,8,batches,3)==
          FOJ_GPU_ORDER_UNSUPPORTED,"incorrect vertex count rejected");
    check(foj_gpu_three_layer_order_guard(vertices,9,batches,2)==
          FOJ_GPU_ORDER_UNSUPPORTED,"incorrect batch count rejected");

    scene(vertices,batches);
    /* Front triangle lies behind middle at one vertex and ahead at
     * another; no global source-over submission order can fix this. */
    vertices[0].z=.25f;
    vertices[1].z=.95f;
    vertices[2].z=.90f;
    check(assess(vertices,batches)==FOJ_GPU_ORDER_UNSAFE,
          "crossing transparent triangles rejected");

    scene(vertices,batches);
    for (unsigned i=0;i<3u;++i)vertices[i].z=.55f;
    check(assess(vertices,batches)==FOJ_GPU_ORDER_UNSAFE,
          "coplanar translucent triangles rejected");
    scene(vertices,batches);
    for (unsigned i=0;i<3u;++i)vertices[i].z=.55f+1e-7f;
    check(assess(vertices,batches)==FOJ_GPU_ORDER_UNSAFE,
          "near-equal depth rejected");

    scene(vertices,batches);
    vertices[0].z=NAN;
    check(assess(vertices,batches)==FOJ_GPU_ORDER_UNSUPPORTED,
          "nonfinite depth rejected");
    scene(vertices,batches);
    vertices[0].w=2.f;
    check(assess(vertices,batches)==FOJ_GPU_ORDER_UNSUPPORTED,
          "nonorthographic vertex rejected");
    scene(vertices,batches);
    vertices[0].x=1.1f;
    check(assess(vertices,batches)==FOJ_GPU_ORDER_UNSUPPORTED,
          "offscreen projected clip coordinate rejected");
    scene(vertices,batches);
    vertices[2].x=vertices[0].x;
    vertices[2].y=vertices[0].y;
    check(assess(vertices,batches)==FOJ_GPU_ORDER_UNSUPPORTED,
          "degenerate front triangle rejected");
    scene(vertices,batches);
    batches[0].texture_index=2u;
    check(assess(vertices,batches)==FOJ_GPU_ORDER_UNSUPPORTED,
          "swapped material binding rejected");

    scene(vertices,batches);
    FojGpuVertex tmp=vertices[0];
    vertices[0]=vertices[2];
    vertices[2]=tmp;
    check(assess(vertices,batches)==FOJ_GPU_ORDER_OK,
          "reverse winding accepted with identical correct depth");

    scene(vertices,batches);
    /* Opaque rear suddenly in front at a shared pixel. */
    for (unsigned i=0;i<3u;++i)vertices[6u+i].z=.99f;
    check(assess(vertices,batches)==FOJ_GPU_ORDER_UNSAFE,
          "opaque rear in front of translucent surface rejected");

    if (failures) {
        fprintf(stderr,"%d native triangle guard failures\n",failures);
        return 1;
    }
    puts("Stage269 native C projected-triangle guard: all assertions passed");
    return 0;
}
