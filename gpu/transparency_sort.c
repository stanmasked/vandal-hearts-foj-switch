#include "transparency_sort.h"
#include <math.h>
#include <string.h>

/* Convex clipping of two projected triangles. All numerical or ambiguous
 * outcomes are rejected; no alpha channel, texture or GPU context involved. */
enum { POLYGON_CAP=12 };
static const double AREA_TOL=1e-9;
static const double DEPTH_TOL=1e-6;
typedef struct { double x,y; } Point;
static Point delta(Point a,Point b) {
    Point p={a.x-b.x,a.y-b.y};return p;
}
static double cross(Point a,Point b){return a.x*b.y-a.y*b.x;}
static double polygon_area2(const Point *p,size_t n){
    double area=0.0;
    for(size_t i=0;i<n;++i)area+=cross(p[i],p[(i+1u)%n]);
    return area;
}
static double edge_side(Point a,Point b,Point p,double winding){
    return winding*cross(delta(b,a),delta(p,a));
}
static int validate(const FojGpuVertex *v){
    Point p[3];
    for(size_t i=0;i<3;++i){
        if(!isfinite(v[i].x)||!isfinite(v[i].y)||!isfinite(v[i].z)||
           !isfinite(v[i].w)||v[i].w!=1.f||
           v[i].x< -1.f||v[i].x>1.f||
           v[i].y< -1.f||v[i].y>1.f||
           v[i].z<0.f||v[i].z>1.f)
           return 0;
        p[i]=(Point){v[i].x,v[i].y};
    }
    return fabs(polygon_area2(p,3))>AREA_TOL;
}
static int intersection(const FojGpuVertex *a,
                        const FojGpuVertex *b,
                        Point *out,size_t *out_count){
    Point current[POLYGON_CAP],next[POLYGON_CAP],boundary[3];
    size_t n=3;
    for(size_t i=0;i<3;++i){
        current[i]=(Point){a[i].x,a[i].y};
        boundary[i]=(Point){b[i].x,b[i].y};
    }
    double orient=polygon_area2(boundary,3)>0.0?1.0:-1.0;
    for(size_t edge=0;edge<3 && n;++edge){
        Point start=boundary[edge],end=boundary[(edge+1u)%3];
        size_t written=0;
        Point prev=current[n-1u];
        double prev_side=edge_side(start,end,prev,orient);
        for(size_t i=0;i<n;++i){
            Point cur=current[i];
            double cur_side=edge_side(start,end,cur,orient);
            int was_inside=prev_side>= -AREA_TOL;
            int is_inside=cur_side>= -AREA_TOL;
            if(was_inside!=is_inside){
                double divisor=prev_side-cur_side;
                if(fabs(divisor)<=1e-15 || written>=POLYGON_CAP)
                    return 0;
                double t=prev_side/divisor;
                if(t<0.)t=0.;
                if(t>1.)t=1.;
                next[written++]=(Point){prev.x+t*(cur.x-prev.x),
                                        prev.y+t*(cur.y-prev.y)};
            }
            if(is_inside){
                if(written>=POLYGON_CAP)return 0;
                next[written++]=cur;
            }
            prev=cur;
            prev_side=cur_side;
        }
        n=written;
        for(size_t i=0;i<n;++i)current[i]=next[i];
    }
    for(size_t i=0;i<n;++i)out[i]=current[i];
    *out_count=n;
    return 1;
}
static double interpolate_z(const FojGpuVertex *v,Point p){
    Point a={v[0].x,v[0].y};
    Point ab={v[1].x-v[0].x,v[1].y-v[0].y};
    Point ac={v[2].x-v[0].x,v[2].y-v[0].y};
    Point ap=delta(p,a);
    double den=cross(ab,ac);
    double wb=cross(ap,ac)/den;
    double wc=cross(ab,ap)/den;
    return (double)v[0].z+wb*((double)v[1].z-v[0].z)
                          +wc*((double)v[2].z-v[0].z);
}
/* No visible projected overlap = 0; first triangle nearer = 1;
 * second triangle nearer = -1; crossing or ambiguous = 2. */
static int pair_precedence(const FojGpuVertex *a,const FojGpuVertex *b){
    Point poly[POLYGON_CAP];
    size_t n=0;
    if(!intersection(a,b,poly,&n))return 2;
    if(n<3 || fabs(polygon_area2(poly,n))<=AREA_TOL)return 0;
    double min_diff=HUGE_VAL,max_diff=-HUGE_VAL;
    for(size_t i=0;i<n;++i){
        double d=interpolate_z(a,poly[i])-interpolate_z(b,poly[i]);
        if(!isfinite(d))return 2;
        if(d<min_diff)min_diff=d;
        if(d>max_diff)max_diff=d;
    }
    if(min_diff>DEPTH_TOL)return 1;
    if(max_diff< -DEPTH_TOL)return -1;
    return 2;
}
FojAlphaSortStatus foj_alpha_sort_back_to_front(
    const FojGpuVertex *vertices,size_t triangle_count,
    uint32_t *output,size_t output_capacity){
    if(!vertices||!output||triangle_count==0u||
       triangle_count>FOJ_ALPHA_SORT_MAX_TRIANGLES||
       output_capacity<triangle_count)return FOJ_ALPHA_SORT_INVALID;
    for(size_t i=0;i<triangle_count;++i)
        if(!validate(vertices+3u*i))return FOJ_ALPHA_SORT_INVALID;

    /* Edges are from FAR to NEAR; one bit per triangle.
     * Data is generated only after all input preflight checks succeed. */
    uint64_t edge[FOJ_ALPHA_SORT_MAX_TRIANGLES]={0};
    unsigned indegree[FOJ_ALPHA_SORT_MAX_TRIANGLES]={0};
    for(size_t i=0;i<triangle_count;++i)
        for(size_t j=i+1u;j<triangle_count;++j){
            int order=pair_precedence(vertices+3u*i,vertices+3u*j);
            if(order==2)return FOJ_ALPHA_SORT_UNSAFE;
            if(order==0)continue;
            size_t far=order==1?j:i;
            size_t near=order==1?i:j;
            edge[far]|=UINT64_C(1)<<near;
            ++indegree[near];
        }

    /* Deterministic Kahn order: smallest available source index wins.
     * On cycles, previously supplied caller output remains untouched. */
    uint32_t result[FOJ_ALPHA_SORT_MAX_TRIANGLES]={0};
    uint64_t processed=0;
    for(size_t step=0;step<triangle_count;++step){
        size_t chosen=triangle_count;
        for(size_t i=0;i<triangle_count;++i)
            if(!(processed&(UINT64_C(1)<<i)) && indegree[i]==0u){
                chosen=i;
                break;
            }
        if(chosen==triangle_count)return FOJ_ALPHA_SORT_UNSAFE;
        result[step]=(uint32_t)chosen;
        processed|=UINT64_C(1)<<chosen;
        for(size_t j=0;j<triangle_count;++j)
            if(edge[chosen]&(UINT64_C(1)<<j))
                --indegree[j];
    }
    memcpy(output,result,triangle_count*sizeof(*output));
    return FOJ_ALPHA_SORT_OK;
}
