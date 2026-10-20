/* Stage272: SDK-free deterministic back-to-front planner regressions. */
#include "transparency_sort.h"
#include <math.h>
#include <stdint.h>
#include <stdio.h>

static unsigned checks=0;
#define CHECK(expr) do {++checks;if(!(expr)){ \
  fprintf(stderr,"stage272 failed line %d: %s\n",__LINE__,#expr);return 1;\
}} while(0)

static void put(FojGpuVertex *p,float x,float y,float z){
    *p=(FojGpuVertex){x,y,z,1.f,0.f,0.f};
}
static void tri(FojGpuVertex *v,float x,float y,float z){
    put(v,x,y,z);
    put(v+1,x+.09f,y,z);
    put(v+2,x,y+.09f,z);
}
int main(void){
    FojGpuVertex v[3*FOJ_ALPHA_SORT_MAX_TRIANGLES]={0};
    uint32_t out[FOJ_ALPHA_SORT_MAX_TRIANGLES];
    for(unsigned i=0;i<FOJ_ALPHA_SORT_MAX_TRIANGLES;++i)
        out[i]=UINT32_C(0xA5A5A5A5);
    tri(v,-.2f,-.2f,.9f);
    tri(v+3,-.2f,-.2f,.5f);
    tri(v+6,-.2f,-.2f,.1f);
    CHECK(foj_alpha_sort_back_to_front(v,3,out,64)==FOJ_ALPHA_SORT_OK);
    CHECK(out[0]==2u&&out[1]==1u&&out[2]==0u);
    CHECK(out[3]==UINT32_C(0xA5A5A5A5));

    tri(v,-.2f,-.2f,.1f);
    tri(v+3,-.2f,-.2f,.5f);
    tri(v+6,-.2f,-.2f,.9f);
    CHECK(foj_alpha_sort_back_to_front(v,3,out,3)==FOJ_ALPHA_SORT_OK);
    CHECK(out[0]==0u&&out[1]==1u&&out[2]==2u);

    tri(v,-.9f,-.7f,.9f);
    tri(v+3,.4f,.5f,.1f);
    CHECK(foj_alpha_sort_back_to_front(v,2,out,2)==FOJ_ALPHA_SORT_OK);
    CHECK(out[0]==0u&&out[1]==1u);
    tri(v,-.2f,-.2f,.2f);
    tri(v+3,-.2f,-.2f,.5f);
    CHECK(foj_alpha_sort_back_to_front(v,2,out,2)==FOJ_ALPHA_SORT_OK);
    CHECK(out[0]==0u&&out[1]==1u);

    out[0]=UINT32_C(0xA5A5A5A5);
    tri(v,-.2f,-.2f,.6f);
    tri(v+3,-.2f,-.2f,.5f);
    v[0].z=.1f;v[1].z=.9f;
    CHECK(foj_alpha_sort_back_to_front(v,2,out,2)==FOJ_ALPHA_SORT_UNSAFE);
    CHECK(out[0]==UINT32_C(0xA5A5A5A5));
    tri(v,-.2f,-.2f,.5f);
    CHECK(foj_alpha_sort_back_to_front(v,2,out,2)==FOJ_ALPHA_SORT_UNSAFE);
    CHECK(out[0]==UINT32_C(0xA5A5A5A5));
    v[0].x=NAN;
    CHECK(foj_alpha_sort_back_to_front(v,2,out,2)==FOJ_ALPHA_SORT_INVALID);
    CHECK(out[0]==UINT32_C(0xA5A5A5A5));
    tri(v,-.2f,-.2f,.5f);
    v[1].w=.4f;
    CHECK(foj_alpha_sort_back_to_front(v,2,out,2)==FOJ_ALPHA_SORT_INVALID);
    tri(v,-.2f,-.2f,.5f);
    v[1].x=3.0f;
    CHECK(foj_alpha_sort_back_to_front(v,2,out,2)==FOJ_ALPHA_SORT_INVALID);
    tri(v,-.2f,-.2f,.5f);
    v[1].x=v[0].x;v[1].y=v[0].y;
    CHECK(foj_alpha_sort_back_to_front(v,2,out,2)==FOJ_ALPHA_SORT_INVALID);
    CHECK(foj_alpha_sort_back_to_front(NULL,2,out,2)==FOJ_ALPHA_SORT_INVALID);
    CHECK(foj_alpha_sort_back_to_front(v,2,NULL,2)==FOJ_ALPHA_SORT_INVALID);
    CHECK(foj_alpha_sort_back_to_front(v,0,out,2)==FOJ_ALPHA_SORT_INVALID);
    CHECK(foj_alpha_sort_back_to_front(v,65,out,65)==FOJ_ALPHA_SORT_INVALID);
    CHECK(foj_alpha_sort_back_to_front(v,2,out,1)==FOJ_ALPHA_SORT_INVALID);

    /* Exercise max supported cardinality and the uint64_t highest bit:
     * 64 small, strictly disjoint triangles must remain index-ordered. */
    for(unsigned i=0;i<64;++i) {
        float x=-.98f+.245f*(float)(i%8);
        float y=-.98f+.245f*(float)(i/8);
        tri(v+3u*i,x,y,.25f);
    }
    CHECK(foj_alpha_sort_back_to_front(v,64,out,64)==FOJ_ALPHA_SORT_OK);
    for(unsigned i=0;i<64;++i)
        CHECK(out[i]==i);
    fprintf(stdout,"Stage272 native transparency topology: %u checks pass\n",checks);
    return 0;
}
