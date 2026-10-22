#include "stage324_corner_tile_clip.h"
#include <math.h>
#include <stdint.h>
#include <string.h>

enum { POLY_CAP=FOJ_STAGE324_MAX_POLYGON_VERTICES };
static const double AREA_EPS=1e-15;
static const float DUP_EPS=1e-7f;

static int overlap(const void *ap,size_t an,const void *bp,size_t bn) {
    const uintptr_t a=(uintptr_t)ap,b=(uintptr_t)bp;
    if(an>UINTPTR_MAX-a || bn>UINTPTR_MAX-b)return 1;
    return a<b+bn && b<a+an;
}
static int finite_vertex(const FojStage324Vertex *v) {
    return isfinite(v->x)&&isfinite(v->y)&&isfinite(v->z)&&
           isfinite(v->u)&&isfinite(v->v)&&
           v->u>=0.0f&&v->u<=1.0f&&v->v>=0.0f&&v->v<=1.0f;
}
static double signed_area2(const FojStage324Vertex *p,unsigned n) {
    double sum=0.0;
    if(n<3u)return 0.0;
    for(unsigned i=0;i<n;++i) {
        const unsigned j=(i+1u)%n;
        sum+=(double)p[i].u*p[j].v-(double)p[j].u*p[i].v;
    }
    return sum;
}
static int same_uv(const FojStage324Vertex *a,const FojStage324Vertex *b) {
    return fabsf(a->u-b->u)<=DUP_EPS&&fabsf(a->v-b->v)<=DUP_EPS;
}
static unsigned append_unique(FojStage324Vertex *out,unsigned n,
                              const FojStage324Vertex *v) {
    if(n && same_uv(out+n-1u,v))return n;
    if(n>=POLY_CAP)return POLY_CAP+1u;
    out[n]=*v;
    return n+1u;
}
static double side(const FojStage324Vertex *p,unsigned edge,double bound) {
    switch(edge) {
        case 0u:return (double)p->u-bound; /* left */
        case 1u:return bound-(double)p->u; /* right */
        case 2u:return (double)p->v-bound; /* top */
        default:return bound-(double)p->v; /* bottom */
    }
}
static FojStage324Vertex mix(const FojStage324Vertex *a,
                             const FojStage324Vertex *b,double t) {
    FojStage324Vertex r;
    r.x=(float)((double)a->x+t*((double)b->x-a->x));
    r.y=(float)((double)a->y+t*((double)b->y-a->y));
    r.z=(float)((double)a->z+t*((double)b->z-a->z));
    r.u=(float)((double)a->u+t*((double)b->u-a->u));
    r.v=(float)((double)a->v+t*((double)b->v-a->v));
    return r;
}
static unsigned clip_edge(const FojStage324Vertex *in,unsigned n,
                          FojStage324Vertex *out,unsigned edge,double bound) {
    if(!n)return 0u;
    unsigned written=0u;
    FojStage324Vertex prev=in[n-1u];
    double dprev=side(&prev,edge,bound);
    int prev_inside=dprev>=0.0;
    for(unsigned i=0u;i<n;++i) {
        const FojStage324Vertex cur=in[i];
        const double dcur=side(&cur,edge,bound);
        const int cur_inside=dcur>=0.0;
        if(prev_inside!=cur_inside) {
            const double denom=dprev-dcur;
            if(denom==0.0)return POLY_CAP+1u;
            const double t=dprev/denom;
            const FojStage324Vertex hit=mix(&prev,&cur,t);
            written=append_unique(out,written,&hit);
            if(written>POLY_CAP)return written;
        }
        if(cur_inside) {
            written=append_unique(out,written,&cur);
            if(written>POLY_CAP)return written;
        }
        prev=cur;dprev=dcur;prev_inside=cur_inside;
    }
    if(written>1u&&same_uv(out,out+written-1u))--written;
    return written;
}
static double polygon_area(const FojStage324Vertex *p,unsigned n) {
    return fabs(signed_area2(p,n))*0.5;
}
static int inside_triangle_non_degenerate(const FojStage324Triangle *t) {
    const double a=((double)t->point[1].u-t->point[0].u)*
                   ((double)t->point[2].v-t->point[0].v)-
                   ((double)t->point[1].v-t->point[0].v)*
                   ((double)t->point[2].u-t->point[0].u);
    return isfinite(a)&&fabs(a)>1e-16;
}

int foj_stage324_clip_triangle_to_corner_tile(
    const FojStage324Triangle *triangle,unsigned px,unsigned py,
    FojStage324Vertex *output,size_t output_capacity,
    FojStage324TileClipReport *report) {
    if(!triangle||!output||!report||px==0u||py==0u||px>=4u||py>=4u||
       output_capacity!=FOJ_STAGE324_MAX_OUTPUT_VERTICES)
        return 0;
    const size_t output_bytes=FOJ_STAGE324_MAX_OUTPUT_VERTICES*sizeof(*output);
    if(overlap(triangle,sizeof(*triangle),output,output_bytes)||
       overlap(triangle,sizeof(*triangle),report,sizeof(*report))||
       overlap(output,output_bytes,report,sizeof(*report)))return 0;
    for(unsigned i=0u;i<3u;++i)
        if(!finite_vertex(triangle->point+i))return 0;
    if(!inside_triangle_non_degenerate(triangle))return 0;

    const double left=((double)px*256.0-8.0)/1024.0;
    const double right=((double)px*256.0+8.0)/1024.0;
    const double top=((double)py*256.0-8.0)/1024.0;
    const double bottom=((double)py*256.0+8.0)/1024.0;
    FojStage324TileClipReport value={0};
    value.atlas_first_x=px*256u-8u;
    value.atlas_first_y=py*256u-8u;
    value.source_uv_bounds[0]=(float)left;
    value.source_uv_bounds[1]=(float)top;
    value.source_uv_bounds[2]=(float)right;
    value.source_uv_bounds[3]=(float)bottom;

    FojStage324Vertex a[POLY_CAP]={{0}},b[POLY_CAP]={{0}};
    memcpy(a,triangle->point,sizeof(triangle->point));
    unsigned n=3u;
    n=clip_edge(a,n,b,0u,left);
    if(n>POLY_CAP)return 0;
    n=clip_edge(b,n,a,1u,right);
    if(n>POLY_CAP)return 0;
    n=clip_edge(a,n,b,2u,top);
    if(n>POLY_CAP)return 0;
    n=clip_edge(b,n,a,3u,bottom);
    if(n>POLY_CAP)return 0;
    if(n>1u&&same_uv(a,a+n-1u))--n;

    FojStage324Vertex staged[FOJ_STAGE324_MAX_OUTPUT_VERTICES]={{0}};
    const double area=polygon_area(a,n);
    if(n>=3u&&area>AREA_EPS) {
        for(unsigned i=0u;i<n;++i) {
            const double tu=((double)a[i].u-left)/(right-left);
            const double tv=((double)a[i].v-top)/(bottom-top);
            if(!isfinite(tu)||!isfinite(tv)||tu < -1e-6||tu > 1.000001||
               tv < -1e-6||tv > 1.000001)return 0;
            a[i].u=(float)(tu<0.0?0.0:(tu>1.0?1.0:tu));
            a[i].v=(float)(tv<0.0?0.0:(tv>1.0?1.0:tv));
        }
        const unsigned out_n=3u*(n-2u);
        if(out_n>FOJ_STAGE324_MAX_OUTPUT_VERTICES)return 0;
        for(unsigned i=1u;i+1u<n;++i) {
            staged[(i-1u)*3u]=a[0];
            staged[(i-1u)*3u+1u]=a[i];
            staged[(i-1u)*3u+2u]=a[i+1u];
        }
        value.clipped_uv_area=area;
        value.polygon_vertices=n;
        value.output_vertices=out_n;
        value.output_triangles=n-2u;
        value.intersects=1u;
    }
    memcpy(output,staged,sizeof(staged));
    *report=value;
    return 1;
}
