#include "stage319_bilinear_halo_support.h"
#include "stage303_bc1_page_uv.h"
#include <math.h>
#include <stdint.h>
#include <string.h>

typedef struct {double u,v;} Point;

static int overlaps(const void *aa,size_t an,const void *bb,size_t bn) {
    const uintptr_t a=(uintptr_t)aa,b=(uintptr_t)bb;
    if(an>UINTPTR_MAX-a||bn>UINTPTR_MAX-b)return 1;
    return a<b+bn && b<a+an;
}

/* Half-planes in UV space: left, right, top, bottom. */
static double side(Point p,unsigned side,double value) {
    switch(side) {
        case 0u:return p.u-value;
        case 1u:return value-p.u;
        case 2u:return p.v-value;
        default:return value-p.v;
    }
}
static unsigned clip(const Point *input,unsigned n,Point *output,
                     unsigned edge,double value) {
    if(!n)return 0u;
    unsigned written=0u;
    Point prev=input[n-1u];
    double previous=side(prev,edge,value);
    for(unsigned i=0u;i<n;++i) {
        const Point current=input[i];
        const double next=side(current,edge,value);
        const int inside_previous=previous>=0.0;
        const int inside_next=next>=0.0;
        if(inside_previous!=inside_next) {
            const double t=previous/(previous-next);
            if(written>=16u)return 0u;
            output[written++]=(Point){
                prev.u+t*(current.u-prev.u),
                prev.v+t*(current.v-prev.v)
            };
        }
        if(inside_next) {
            if(written>=16u)return 0u;
            output[written++]=current;
        }
        prev=current;
        previous=next;
    }
    return written;
}
static double area(const Point *p,unsigned n) {
    if(n<3u)return 0.0;
    double total=0.0;
    for(unsigned i=1u;i+1u<n;++i) {
        const double ax=p[i].u-p[0].u,ay=p[i].v-p[0].v;
        const double bx=p[i+1u].u-p[0].u,by=p[i+1u].v-p[0].v;
        total+=ax*by-ay*bx;
    }
    return fabs(total)*0.5;
}
static int polygon_intersects_expanded(
    const Point tri[3],double left,double right,
    double top,double bottom) {
    Point a[16],b[16];
    memcpy(a,tri,3u*sizeof(Point));
    unsigned n=3u;
    n=clip(a,n,b,0u,left);
    n=clip(b,n,a,1u,right);
    n=clip(a,n,b,2u,top);
    n=clip(b,n,a,3u,bottom);
    /* Area is measured in normalized UV^2. A tiny numerical artifact
     * from an exactly tangent edge must not claim a new page. */
    return area(a,n)>1e-16;
}
int foj_stage319_triangle_bilinear_pages(
    const FojStage318Triangle *triangle,FojStage319FilterSupport *out) {
    if(!triangle||!out||
       overlaps(triangle,sizeof(*triangle),out,sizeof(*out)))return 0;
    FojStage318Coverage geometric={0};
    if(!foj_stage318_triangle_page_coverage(triangle,&geometric))return 0;
    const double halo=0.5/(double)FOJ_BC1_SOURCE_EDGE;
    Point points[3];
    for(unsigned i=0u;i<3u;++i) {
        points[i]=(Point){
            (double)triangle->point[i].u,
            (double)triangle->point[i].v
        };
    }
    FojStage319FilterSupport result={0};
    result.geometry_page_mask=geometric.page_mask;
    result.geometry_pages=geometric.pages_covered;
    result.filter_halo_uv=halo;
    for(unsigned y=0u;y<4u;++y)for(unsigned x=0u;x<4u;++x) {
        double left=(double)x/4.0-halo;
        double right=(double)(x+1u)/4.0+halo;
        double top=(double)y/4.0-halo;
        double bottom=(double)(y+1u)/4.0+halo;
        if(left<0.0)left=0.0;
        if(right>1.0)right=1.0;
        if(top<0.0)top=0.0;
        if(bottom>1.0)bottom=1.0;
        if(polygon_intersects_expanded(points,left,right,top,bottom))
            result.filter_page_mask|=(uint16_t)(1u<<(y*4u+x));
    }
    if((result.filter_page_mask&result.geometry_page_mask)!=
        result.geometry_page_mask)return 0;
    result.halo_only_page_mask=(uint16_t)(
        result.filter_page_mask&~result.geometry_page_mask);
    for(unsigned i=0u;i<16u;++i) {
        result.filter_pages+=(result.filter_page_mask>>i)&1u;
        result.halo_only_pages+=(result.halo_only_page_mask>>i)&1u;
    }
    if(result.filter_pages==0u ||
       result.filter_pages<result.geometry_pages ||
       result.halo_only_pages+result.geometry_pages!=result.filter_pages)
        return 0;
    *out=result;
    return 1;
}
