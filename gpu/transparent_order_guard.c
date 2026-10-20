/* Stage269 native fail-closed projected triangle overlap depth guard.
 * Orthographic Stage267 research coordinates only (W=1, Z GREATER).
 * Never claims polygon splitting, general OIT, or original FoJ rendering.
 */
#include "transparent_order_guard.h"
#include <math.h>
#include <stdint.h>

enum { MAX_CLIPPED_POINTS=16 };
static const float kAreaEps=1e-7f;
static const float kDepthEps=1e-5f;
typedef struct { float x,y; } Point;
typedef struct { Point p[3]; float z[3]; } Triangle;

static float cross(Point a,Point b) {
    return a.x*b.y-a.y*b.x;
}
static Point subtract(Point a,Point b) {
    Point p={a.x-b.x,a.y-b.y};
    return p;
}
static float tri_area(const Triangle *t) {
    return cross(subtract(t->p[1],t->p[0]),
                 subtract(t->p[2],t->p[0]));
}
static float twice_area(const Point *p,int count) {
    float a=0.f;
    for (int i=0;i<count;++i)
        a+=cross(p[i],p[(i+1)%count]);
    return a;
}
static float inside(Point a,Point b,Point p,float sign) {
    return sign*cross(subtract(b,a),subtract(p,a));
}
static int polygon_clip(const Triangle *subject,const Triangle *boundary,
                        Point out[MAX_CLIPPED_POINTS]) {
    Point current[MAX_CLIPPED_POINTS];
    int count=3;
    for (int i=0;i<3;++i)current[i]=subject->p[i];
    const float sign=tri_area(boundary)>0.f?1.f:-1.f;
    for (int edge=0;edge<3;++edge) {
        const Point a=boundary->p[edge];
        const Point b=boundary->p[(edge+1)%3];
        Point next[MAX_CLIPPED_POINTS];
        int written=0;
        if (!count)return 0;
        Point previous=current[count-1];
        float previous_d=inside(a,b,previous,sign);
        for (int j=0;j<count;++j) {
            const Point p=current[j];
            const float d=inside(a,b,p,sign);
            const int previous_good=previous_d>=-kAreaEps;
            const int good=d>=-kAreaEps;
            if (previous_good!=good) {
                const float denom=previous_d-d;
                if (fabsf(denom)<1e-12f)return -1;
                float t=previous_d/denom;
                if (t<0.f)t=0.f;
                if (t>1.f)t=1.f;
                if (written>=MAX_CLIPPED_POINTS)return -1;
                next[written++]=(Point){
                    previous.x+t*(p.x-previous.x),
                    previous.y+t*(p.y-previous.y)
                };
            }
            if (good) {
                if (written>=MAX_CLIPPED_POINTS)return -1;
                next[written++]=p;
            }
            previous=p;
            previous_d=d;
        }
        count=written;
        for (int j=0;j<count;++j)current[j]=next[j];
    }
    for (int i=0;i<count;++i)out[i]=current[i];
    return count;
}
static int interpolate_z(const Triangle *t,Point p,float *z) {
    const Point ab=subtract(t->p[1],t->p[0]);
    const Point ac=subtract(t->p[2],t->p[0]);
    const Point ap=subtract(p,t->p[0]);
    const float denom=cross(ab,ac);
    if (fabsf(denom)<=kAreaEps)return 0;
    const float u=cross(ap,ac)/denom;
    const float v=cross(ab,ap)/denom;
    *z=t->z[0]+u*(t->z[1]-t->z[0])+v*(t->z[2]-t->z[0]);
    return isfinite(*z)!=0;
}
static int nearer_over_overlap(const Triangle *near,
                               const Triangle *far) {
    Point polygon[MAX_CLIPPED_POINTS];
    const int count=polygon_clip(near,far,polygon);
    if (count<0)return 0;
    /* Point/edge contact does not have common interior to composite. */
    if (count<3 || fabsf(twice_area(polygon,count))<=kAreaEps)
        return 1;
    for (int i=0;i<count;++i) {
        float front_z=0.f,rear_z=0.f;
        if (!interpolate_z(near,polygon[i],&front_z) ||
            !interpolate_z(far,polygon[i],&rear_z) ||
            !(front_z-rear_z>kDepthEps))
            return 0;
    }
    return 1;
}
FojGpuOrderStatus foj_gpu_three_layer_order_guard(
    const FojGpuVertex *vertices,size_t vertex_count,
    const FojGpuBatch *batches,size_t batch_count) {
    if (!vertices || !batches)return FOJ_GPU_ORDER_ARGUMENT;
    if (vertex_count!=9u || batch_count!=3u)
        return FOJ_GPU_ORDER_UNSUPPORTED;
    Triangle tri[3];
    for (unsigned i=0;i<3u;++i) {
        if (batches[i].first_vertex!=i*3u ||
            batches[i].vertex_count!=3u ||
            batches[i].texture_index!=i)
            return FOJ_GPU_ORDER_UNSUPPORTED;
        for (unsigned j=0;j<3u;++j) {
            const FojGpuVertex *v=&vertices[i*3u+j];
            if (!isfinite(v->x) || !isfinite(v->y) ||
                !isfinite(v->z) || !isfinite(v->w) ||
                v->x< -1.f || v->x>1.f ||
                v->y< -1.f || v->y>1.f ||
                v->z<0.f || v->z>1.f ||
                fabsf(v->w-1.f)>1e-5f)
                return FOJ_GPU_ORDER_UNSUPPORTED;
            tri[i].p[j]=(Point){v->x,v->y};
            tri[i].z[j]=v->z;
        }
        if (fabsf(tri_area(&tri[i]))<=kAreaEps)
            return FOJ_GPU_ORDER_UNSUPPORTED;
    }
    /* Draw order: cool opaque 2 first, warm 1 then violet 0.
     * The depth buffer does not resolve transparent/transparent crossings,
     * because transparent draws must have depth writes disabled. */
    if (!nearer_over_overlap(&tri[1],&tri[2]) ||
        !nearer_over_overlap(&tri[0],&tri[2]) ||
        !nearer_over_overlap(&tri[0],&tri[1]))
        return FOJ_GPU_ORDER_UNSAFE;
    return FOJ_GPU_ORDER_OK;
}
const char *foj_gpu_order_status_name(FojGpuOrderStatus s) {
    switch(s) {
        case FOJ_GPU_ORDER_OK:return "safe fixed three-layer order";
        case FOJ_GPU_ORDER_ARGUMENT:return "missing order inputs";
        case FOJ_GPU_ORDER_UNSUPPORTED:return "unsupported research geometry";
        case FOJ_GPU_ORDER_UNSAFE:return "unsafe triangle depth order";
        default:return "unknown order status";
    }
}
