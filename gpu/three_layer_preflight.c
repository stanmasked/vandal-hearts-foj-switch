#include "three_layer_preflight.h"
#include <math.h>
#include <stdint.h>

/* Conservative clipping for exactly two convex 3-vertex polygons.
 * The overlap polygon cannot exceed 6 points, but intermediate capacity
 * 12 is defensive. Any numerical uncertainty fails closed. */
enum { POLY_CAPACITY=12, LAYERS=3, VERTICES_PER_LAYER=3 };
static const double AREA_EPS=1e-10;
static const double DEPTH_EPS=1e-6;
typedef struct { double x,y; } Pt;

static double cross(Pt a,Pt b) {return a.x*b.y-a.y*b.x;}
static Pt sub(Pt a,Pt b) {Pt c={a.x-b.x,a.y-b.y};return c;}
static double area2(const Pt *p,unsigned n) {
    double s=0;
    for(unsigned i=0;i<n;++i)s+=cross(p[i],p[(i+1u)%n]);
    return s;
}
static double side(Pt a,Pt b,Pt p,double sign) {
    return sign*cross(sub(b,a),sub(p,a));
}

static int valid_triangle(const FojGpuVertex *v) {
    Pt p[3];
    for(unsigned k=0;k<3;++k) {
        if (!isfinite(v[k].x)||!isfinite(v[k].y)||
            !isfinite(v[k].z)||!isfinite(v[k].w)||
            v[k].x< -1.f||v[k].x>1.f||
            v[k].y< -1.f||v[k].y>1.f||
            v[k].z<0.f||v[k].z>1.f||v[k].w!=1.f)
            return 0;
        p[k]=(Pt){v[k].x,v[k].y};
    }
    return fabs(area2(p,3))>AREA_EPS;
}
static int clip_triangles(const FojGpuVertex *a,
                          const FojGpuVertex *b,
                          Pt *output,unsigned *written) {
    Pt current[POLY_CAPACITY],scratch[POLY_CAPACITY],mask[3];
    unsigned count=3;
    for(unsigned k=0;k<3;++k) {
        current[k]=(Pt){a[k].x,a[k].y};
        mask[k]=(Pt){b[k].x,b[k].y};
    }
    const double orient=area2(mask,3)>0.0?1.0:-1.0;
    for(unsigned edge=0;edge<3;++edge) {
        if (!count)break;
        const Pt start=mask[edge],end=mask[(edge+1u)%3];
        unsigned next_count=0;
        Pt previous=current[count-1u];
        double prev_side=side(start,end,previous,orient);
        for(unsigned k=0;k<count;++k) {
            const Pt next=current[k];
            const double next_side=side(start,end,next,orient);
            const int old_inside=prev_side>= -AREA_EPS;
            const int new_inside=next_side>= -AREA_EPS;
            if(old_inside!=new_inside) {
                const double divisor=prev_side-next_side;
                if (fabs(divisor)<1e-15 || next_count>=POLY_CAPACITY)
                    return 0;
                double t=prev_side/divisor;
                if(t<0.0)t=0.0;
                if(t>1.0)t=1.0;
                scratch[next_count++]=(Pt){
                    previous.x + t*(next.x-previous.x),
                    previous.y + t*(next.y-previous.y)
                };
            }
            if(new_inside) {
                if (next_count>=POLY_CAPACITY)return 0;
                scratch[next_count++]=next;
            }
            previous=next;
            prev_side=next_side;
        }
        count=next_count;
        for(unsigned k=0;k<count;++k)current[k]=scratch[k];
    }
    for(unsigned k=0;k<count;++k)output[k]=current[k];
    *written=count;
    return 1;
}
static double depth_at(const FojGpuVertex *v,Pt p) {
    const Pt a={v[0].x,v[0].y};
    const Pt ab={v[1].x-v[0].x,v[1].y-v[0].y};
    const Pt ac={v[2].x-v[0].x,v[2].y-v[0].y};
    const Pt ap=sub(p,a);
    const double denominator=cross(ab,ac);
    const double wb=cross(ap,ac)/denominator;
    const double wc=cross(ab,ap)/denominator;
    return (double)v[0].z + wb*((double)v[1].z-v[0].z)
                      + wc*((double)v[2].z-v[0].z);
}
/* All three input layers use one global [0,1] depth mapping.
 * Since zA-zB varies affinely over the common convex polygon, strict
 * front-ness at every polygon vertex certifies the entire interior. */
static FojThreeOrderStatus relation(const FojGpuVertex *near,
                                     const FojGpuVertex *far) {
    Pt intersection[POLY_CAPACITY];
    unsigned n=0;
    if (!clip_triangles(near,far,intersection,&n))
        return FOJ_THREE_ORDER_UNSAFE;
    if(n<3 || fabs(area2(intersection,n))<=AREA_EPS)
        return FOJ_THREE_ORDER_OK;
    for(unsigned k=0;k<n;++k) {
        const double depth_near=depth_at(near,intersection[k]);
        const double depth_far=depth_at(far,intersection[k]);
        if (!isfinite(depth_near)||!isfinite(depth_far)||
            depth_near-depth_far<=DEPTH_EPS)
            return FOJ_THREE_ORDER_UNSAFE;
    }
    return FOJ_THREE_ORDER_OK;
}
FojThreeOrderStatus foj_three_layer_preflight(
    const FojGpuVertex *vertices,size_t vertex_count,
    const FojGpuBatch *batches,size_t batch_count) {
    if (!vertices||!batches||vertex_count!=9u||batch_count!=LAYERS)
        return FOJ_THREE_ORDER_INVALID;
    for(unsigned i=0;i<LAYERS;++i) {
        if (batches[i].first_vertex!=i*VERTICES_PER_LAYER||
            batches[i].vertex_count!=VERTICES_PER_LAYER||
            batches[i].texture_index!=i ||
            !valid_triangle(vertices+i*VERTICES_PER_LAYER))
            return FOJ_THREE_ORDER_INVALID;
    }
    for(unsigned nearer=0;nearer<LAYERS;++nearer)
        for(unsigned farther=nearer+1u;farther<LAYERS;++farther) {
            const FojThreeOrderStatus s=relation(
                vertices+nearer*VERTICES_PER_LAYER,
                vertices+farther*VERTICES_PER_LAYER);
            if(s!=FOJ_THREE_ORDER_OK)return s;
        }
    return FOJ_THREE_ORDER_OK;
}
