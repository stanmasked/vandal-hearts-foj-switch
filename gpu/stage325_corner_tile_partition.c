#include "stage325_corner_tile_partition.h"
#include <math.h>
#include <stdint.h>
#include <string.h>

enum { POLY_CAP=FOJ_STAGE325_MAX_POLYGON_VERTICES };

static int overlap(const void *ap,size_t an,const void *bp,size_t bn) {
    const uintptr_t a=(uintptr_t)ap,b=(uintptr_t)bp;
    if(an>UINTPTR_MAX-a || bn>UINTPTR_MAX-b)return 1;
    return a<b+bn && b<a+an;
}
static double signed_area2(const FojStage325Vertex *p,unsigned n) {
    double sum=0.0;
    if(n<3u)return 0.0;
    for(unsigned i=0u;i<n;++i) {
        const unsigned j=(i+1u)%n;
        sum+=(double)p[i].u*p[j].v-(double)p[j].u*p[i].v;
    }
    return sum;
}
static double polygon_area(const FojStage325Vertex *p,unsigned n) {
    return fabs(signed_area2(p,n))*0.5;
}
static int same_uv(const FojStage325Vertex *a,const FojStage325Vertex *b) {
    return a->u==b->u&&a->v==b->v;
}
static unsigned append_unique(FojStage325Vertex *out,unsigned n,
                              const FojStage325Vertex *v) {
    if(n && same_uv(out+n-1u,v))return n;
    if(n>=POLY_CAP)return POLY_CAP+1u;
    out[n]=*v;
    return n+1u;
}
static double side(const FojStage325Vertex *p,unsigned edge,double bound) {
    switch(edge) {
        case 0u:return (double)p->u-bound;
        case 1u:return bound-(double)p->u;
        case 2u:return (double)p->v-bound;
        default:return bound-(double)p->v;
    }
}
static FojStage325Vertex mix_at_edge(const FojStage325Vertex *a,
                                     const FojStage325Vertex *b,
                                     double t,unsigned edge,double bound) {
    FojStage325Vertex r;
    r.x=(float)((double)a->x+t*((double)b->x-a->x));
    r.y=(float)((double)a->y+t*((double)b->y-a->y));
    r.z=(float)((double)a->z+t*((double)b->z-a->z));
    r.u=(float)((double)a->u+t*((double)b->u-a->u));
    r.v=(float)((double)a->v+t*((double)b->v-a->v));
    if(edge<2u)r.u=(float)bound;
    else r.v=(float)bound;
    return r;
}
/* Keep the positive side for the tile polygon; negative side is the
 * complementary piece emitted at this edge. Both retain input winding. */
static unsigned clip_half(const FojStage325Vertex *in,unsigned n,
                          FojStage325Vertex *out,unsigned edge,double bound,
                          int keep_positive) {
    if(!n)return 0u;
    unsigned written=0u;
    FojStage325Vertex prev=in[n-1u];
    double dprev=side(&prev,edge,bound);
    int prev_inside=keep_positive?(dprev>=0.0):(dprev<=0.0);
    for(unsigned i=0u;i<n;++i) {
        const FojStage325Vertex cur=in[i];
        const double dcur=side(&cur,edge,bound);
        const int cur_inside=keep_positive?(dcur>=0.0):(dcur<=0.0);
        if(prev_inside!=cur_inside) {
            const double denom=dprev-dcur;
            if(denom==0.0)return POLY_CAP+1u;
            const double t=dprev/denom;
            const FojStage325Vertex hit=mix_at_edge(&prev,&cur,t,edge,bound);
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
static int emit_fan(const FojStage325Vertex *poly,unsigned n,
                    FojStage325Vertex *out,unsigned capacity,
                    unsigned *written,double *area_sum) {
    const double area=polygon_area(poly,n);
    if(n<3u||!(area>0.0))return 1;
    const unsigned count=3u*(n-2u);
    if(*written>capacity||count>capacity-*written)return 0;
    for(unsigned i=1u;i+1u<n;++i) {
        out[*written]=poly[0];
        out[*written+1u]=poly[i];
        out[*written+2u]=poly[i+1u];
        *written+=3u;
    }
    *area_sum+=area;
    return 1;
}
int foj_stage325_partition_triangle_at_corner_tile(
    const FojStage325Triangle *triangle,unsigned px,unsigned py,
    FojStage325Vertex *tile_output,size_t tile_capacity,
    FojStage325Vertex *remainder_output,size_t remainder_capacity,
    FojStage325PartitionReport *report) {
    if(!triangle||!tile_output||!remainder_output||!report||
       px==0u||py==0u||px>=4u||py>=4u||
       tile_capacity!=FOJ_STAGE325_TILE_VERTICES||
       remainder_capacity!=FOJ_STAGE325_REMAINDER_VERTICES)
        return 0;
    const size_t tile_bytes=FOJ_STAGE325_TILE_VERTICES*sizeof(*tile_output);
    const size_t remainder_bytes=
        FOJ_STAGE325_REMAINDER_VERTICES*sizeof(*remainder_output);
    if(overlap(triangle,sizeof(*triangle),tile_output,tile_bytes)||
       overlap(triangle,sizeof(*triangle),remainder_output,remainder_bytes)||
       overlap(triangle,sizeof(*triangle),report,sizeof(*report))||
       overlap(tile_output,tile_bytes,remainder_output,remainder_bytes)||
       overlap(tile_output,tile_bytes,report,sizeof(*report))||
       overlap(remainder_output,remainder_bytes,report,sizeof(*report)))
        return 0;
    const double left=((double)px*256.0-8.0)/1024.0;
    const double right=((double)px*256.0+8.0)/1024.0;
    const double top=((double)py*256.0-8.0)/1024.0;
    const double bottom=((double)py*256.0+8.0)/1024.0;
    FojStage325PartitionReport value;
    memset(&value,0,sizeof(value));
    value.atlas_first_x=px*256u-8u;
    value.atlas_first_y=py*256u-8u;
    value.source_uv_bounds[0]=(float)left;
    value.source_uv_bounds[1]=(float)top;
    value.source_uv_bounds[2]=(float)right;
    value.source_uv_bounds[3]=(float)bottom;
    value.input_uv_area=polygon_area(triangle->point,3u);

    FojStage325Vertex tile_stage[FOJ_STAGE325_TILE_VERTICES]={{0}};
    FojStage325Vertex remainder_stage[FOJ_STAGE325_REMAINDER_VERTICES]={{0}};
    FojStage325Vertex current[POLY_CAP]={{0}};
    FojStage325Vertex next[POLY_CAP]={{0}};
    FojStage325Vertex outside[POLY_CAP]={{0}};
    FojStage324TileClipReport tile_report;
    memset(&tile_report,0,sizeof(tile_report));
    if(!foj_stage324_clip_triangle_to_corner_tile(
        triangle,px,py,tile_stage,FOJ_STAGE324_MAX_OUTPUT_VERTICES,
        &tile_report))return 0;
    memcpy(current,triangle->point,sizeof(triangle->point));
    unsigned n=3u,tile_written=tile_report.output_vertices;
    unsigned remainder_written=0u;
    double remainder_area=0.0;
    value.tile_uv_area=tile_report.clipped_uv_area;
    value.tile_intersects=tile_report.intersects;

    const double bounds[4]={left,right,top,bottom};
    for(unsigned edge=0u;edge<4u;++edge) {
        const unsigned outside_n=clip_half(current,n,outside,edge,bounds[edge],0);
        if(outside_n>POLY_CAP)return 0;
        if(!emit_fan(outside,outside_n,remainder_stage,
                     FOJ_STAGE325_REMAINDER_VERTICES,&remainder_written,
                     &remainder_area))return 0;
        const unsigned next_n=clip_half(current,n,next,edge,bounds[edge],1);
        if(next_n>POLY_CAP)return 0;
        memcpy(current,next,sizeof(current));
        n=next_n;
    }

    value.remainder_uv_area=remainder_area;
    value.tile_vertices=tile_written;
    value.tile_triangles=tile_written/3u;
    value.remainder_vertices=remainder_written;
    value.remainder_triangles=remainder_written/3u;
    memcpy(tile_output,tile_stage,sizeof(tile_stage));
    memcpy(remainder_output,remainder_stage,sizeof(remainder_stage));
    memcpy(report,&value,sizeof(value));
    return 1;
}
