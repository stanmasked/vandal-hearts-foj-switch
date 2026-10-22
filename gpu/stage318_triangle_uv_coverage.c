#include "stage318_triangle_uv_coverage.h"
#include <math.h>
#include <stdint.h>
#include <string.h>

typedef struct { double u,v; } Point;
static int overlaps(const void *aa,size_t an,const void *bb,size_t bn) {
    const uintptr_t a=(uintptr_t)aa,b=(uintptr_t)bb;
    if(an>UINTPTR_MAX-a || bn>UINTPTR_MAX-b)return 1;
    return a<b+bn && b<a+an;
}
static double signed_distance(Point p,unsigned edge,double value) {
    switch(edge) {
        case 0u:return p.u-value;  /* u >= page left */
        case 1u:return value-p.u;  /* u <= page right */
        case 2u:return p.v-value;  /* v >= page upper */
        default:return value-p.v;  /* v <= page lower */
    }
}
/* Clip a convex input polygon against one closed half-plane. */
static unsigned clip(const Point *in,unsigned n,Point *out,
                     unsigned edge,double value) {
    if (!n)return 0u;
    unsigned count=0u;
    Point previous=in[n-1u];
    double prev=signed_distance(previous,edge,value);
    for(unsigned k=0u;k<n;++k) {
        const Point current=in[k];
        const double next=signed_distance(current,edge,value);
        const int was_inside=prev>=0.0,now_inside=next>=0.0;
        if (was_inside!=now_inside) {
            const double t=prev/(prev-next);
            if (count>=16u)return 0u;
            out[count++]=(Point){
                previous.u+(current.u-previous.u)*t,
                previous.v+(current.v-previous.v)*t
            };
        }
        if (now_inside) {
            if(count>=16u)return 0u;
            out[count++]=current;
        }
        previous=current;
        prev=next;
    }
    return count;
}
static double poly_area(const Point *poly,unsigned n) {
    if(n<3u)return 0.0;
    /* Fan triangulation avoids subtracting large non-local shoelace sums. */
    double sum=0.0;
    for(unsigned k=1u;k+1u<n;++k) {
        const double ax=poly[k].u-poly[0].u;
        const double ay=poly[k].v-poly[0].v;
        const double bx=poly[k+1u].u-poly[0].u;
        const double by=poly[k+1u].v-poly[0].v;
        sum+=ax*by-ay*bx;
    }
    return fabs(sum)*0.5;
}
int foj_stage318_triangle_page_coverage(
    const FojStage318Triangle *tri,FojStage318Coverage *out) {
    if (!tri || !out ||
        overlaps(tri,sizeof(*tri),out,sizeof(*out)))return 0;
    Point original[3];
    double min_u=1.0,max_u=0.0,min_v=1.0,max_v=0.0;
    for(unsigned k=0u;k<3u;++k) {
        const float u=tri->point[k].u,v=tri->point[k].v;
        if(!isfinite(u)||!isfinite(v)||
           u<0.f||u>1.f||v<0.f||v>1.f)return 0;
        original[k]=(Point){(double)u,(double)v};
        if(u<min_u)min_u=u;if(u>max_u)max_u=u;
        if(v<min_v)min_v=v;if(v>max_v)max_v=v;
    }
    const double area=poly_area(original,3u);
    if(area<=1e-10)return 0;
    FojStage318Coverage result={0};
    result.triangle_area_uv=area;
    for(unsigned i=1u;i<=3u;++i) {
        const double boundary=(double)i/4.0;
        result.vertical_page_boundaries_crossed+=
            (unsigned)(min_u<boundary&&max_u>boundary);
        result.horizontal_page_boundaries_crossed+=
            (unsigned)(min_v<boundary&&max_v>boundary);
    }
    for(unsigned py=0u;py<4u;++py)for(unsigned px=0u;px<4u;++px) {
        Point a[16],b[16];
        memcpy(a,original,sizeof(original));
        unsigned n=3u;
        n=clip(a,n,b,0u,(double)px/4.0);
        n=clip(b,n,a,1u,(double)(px+1u)/4.0);
        n=clip(a,n,b,2u,(double)py/4.0);
        n=clip(b,n,a,3u,(double)(py+1u)/4.0);
        const double portion=poly_area(a,n);
        const unsigned page=py*4u+px;
        if(portion>1e-13) {
            result.page_mask|=(uint16_t)(1u<<page);
            ++result.pages_covered;
            result.page_area_uv[page]=portion;
            result.covered_area_uv+=portion;
        }
    }
    /* Fail if a numerically significant slice vanished during clipping.
     * This also catches an unexpected unsupported clipping topology. */
    if(result.pages_covered==0u ||
       fabs(result.covered_area_uv-area)>fmax(1e-12,area*1e-8))
        return 0;
    *out=result;
    return 1;
}
