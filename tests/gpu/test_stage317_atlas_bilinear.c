/* Stage317 synthetic atlas: 9 inner four-way corners and clamped edges. */
#include "stage317_atlas_bilinear.h"
#include <assert.h>
#include <math.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

enum { LEN=FOJ_BC1_PAGE_RGBA_BYTES, PAGE=256 };
static uint8_t *owned[16];
static const uint8_t *pages[16];
static size_t sizes[16];
static uint64_t original_hash[16];
static uint8_t channel(unsigned px,unsigned py,unsigned lx,unsigned ly,
                       unsigned c) {
    switch(c) {
    case 0: return (uint8_t)(lx+px*7u+py*13u);
    case 1: return (uint8_t)(ly+px*11u+py*3u);
    case 2: return (uint8_t)(px*60u+py*14u+((lx^ly)&15u));
    default:return (uint8_t)(128u+px*2u+py*5u+((lx+ly)&31u));
    }
}
static uint64_t hash_page(const uint8_t *src) {
    uint64_t h=UINT64_C(1469598103934665603);
    for(size_t i=0;i<LEN;++i) {
        h^=src[i];
        h*=UINT64_C(1099511628211);
    }
    return h;
}
static void init(void) {
    for(unsigned i=0;i<16u;++i) {
        owned[i]=(uint8_t*)malloc(LEN);
        assert(owned[i]);
        const unsigned px=i%4u,py=i/4u;
        for(unsigned y=0;y<PAGE;++y)
            for(unsigned x=0;x<PAGE;++x)
                for(unsigned k=0;k<4u;++k)
                    owned[i][((size_t)y*PAGE+x)*4u+k]=
                        channel(px,py,x,y,k);
        pages[i]=owned[i];
        sizes[i]=LEN;
        original_hash[i]=hash_page(owned[i]);
    }
}
static uint8_t oracle_texel(unsigned ax,unsigned ay,unsigned channel_id) {
    return channel(ax/256u,ay/256u,ax%256u,ay%256u,channel_id);
}
static void validate_source(const FojStage317RoutingReport *r,
                            const unsigned xs[4],const unsigned ys[4]) {
    for(unsigned i=0;i<4u;++i) {
        assert(r->texel[i].atlas_x==xs[i]);
        assert(r->texel[i].atlas_y==ys[i]);
        assert(r->texel[i].page_x==xs[i]/256u);
        assert(r->texel[i].page_y==ys[i]/256u);
        assert(r->texel[i].local_x==xs[i]%256u);
        assert(r->texel[i].local_y==ys[i]%256u);
    }
}
static void nine_intersections(void) {
    unsigned samples=0;
    for(unsigned page_y=1u;page_y<4u;++page_y)
      for(unsigned page_x=1u;page_x<4u;++page_x)
        for(unsigned iy=0u;iy<=4u;++iy)
          for(unsigned ix=0u;ix<=4u;++ix) {
            const unsigned xb=page_x*256u,yb=page_y*256u;
            const float u=((float)xb-0.5f+(float)ix/4.f)/1024.f;
            const float v=((float)yb-0.5f+(float)iy/4.f)/1024.f;
            const unsigned xs[4]={xb-1u,xb,xb-1u,xb};
            const unsigned ys[4]={yb-1u,yb-1u,yb,yb};
            uint8_t got[4]={0};
            FojStage317RoutingReport r={0};
            assert(foj_stage317_sample_atlas(pages,sizes,u,v,got,&r));
            validate_source(&r,xs,ys);
            assert(r.distinct_pages==4u);
            assert(r.crosses_page_x==1u&&r.crosses_page_y==1u);
            for(unsigned k=0;k<4u;++k) {
                const unsigned nw=oracle_texel(xs[0],ys[0],k);
                const unsigned ne=oracle_texel(xs[1],ys[1],k);
                const unsigned sw=oracle_texel(xs[2],ys[2],k);
                const unsigned se=oracle_texel(xs[3],ys[3],k);
                const unsigned weighted=
                    nw*(4u-ix)*(4u-iy)+ne*ix*(4u-iy)+
                    sw*(4u-ix)*iy+se*ix*iy;
                const unsigned expected=(weighted+8u)/16u;
                assert(got[k]==expected);
            }
            ++samples;
          }
    assert(samples==225u);
}
static void straight_edges_and_outer_clamp(void) {
    for(unsigned boundary=1u;boundary<4u;++boundary) {
        const unsigned xb=boundary*256u;
        for(unsigned y=1u;y<1023u;y+=53u) {
            uint8_t out[4];
            FojStage317RoutingReport r={0};
            const float u=(float)xb/1024.f;
            const float v=((float)y+0.5f)/1024.f;
            assert(foj_stage317_sample_atlas(pages,sizes,u,v,out,&r));
            assert(r.distinct_pages==2u);
            assert(r.crosses_page_x==1u&&r.crosses_page_y==0u);
            for(unsigned k=0;k<4u;++k) {
                const unsigned sum=oracle_texel(xb-1u,y,k)+
                                   oracle_texel(xb,y,k);
                assert(out[k]==(sum+1u)/2u);
            }
        }
        const unsigned yb=boundary*256u;
        for(unsigned x=1u;x<1023u;x+=47u) {
            uint8_t out[4];
            FojStage317RoutingReport r={0};
            assert(foj_stage317_sample_atlas(
                pages,sizes,((float)x+0.5f)/1024.f,
                (float)yb/1024.f,out,&r));
            assert(r.distinct_pages==2u);
            assert(r.crosses_page_x==0u&&r.crosses_page_y==1u);
            for(unsigned k=0;k<4u;++k) {
                const unsigned sum=oracle_texel(x,yb-1u,k)+
                                   oracle_texel(x,yb,k);
                assert(out[k]==(sum+1u)/2u);
            }
        }
    }
    /* Clamping both normalized axes to the four outer atlas corners. */
    for(unsigned ix=0;ix<2u;++ix)for(unsigned iy=0;iy<2u;++iy) {
        const float u=ix?1.f:0.f,v=iy?1.f:0.f;
        const unsigned ax=ix?1023u:0u,ay=iy?1023u:0u;
        uint8_t out[4]={0};FojStage317RoutingReport r={0};
        assert(foj_stage317_sample_atlas(pages,sizes,u,v,out,&r));
        assert(r.distinct_pages==1u);
        assert(!r.crosses_page_x && !r.crosses_page_y);
        for(unsigned k=0;k<4u;++k)
            assert(out[k]==oracle_texel(ax,ay,k));
    }
    /* An ordinary four-texel sample does not falsely cross page edges. */
    const float u=400.f/1024.f,v=600.f/1024.f;
    uint8_t out[4]={0};FojStage317RoutingReport r={0};
    assert(foj_stage317_sample_atlas(pages,sizes,u,v,out,&r));
    assert(r.distinct_pages==1u);
    assert(!r.crosses_page_x&&!r.crosses_page_y);
}
static void rejection_and_immutability(void) {
    uint8_t out[4]={9u,8u,7u,6u},old[4];
    memcpy(old,out,4u);
    FojStage317RoutingReport r={0};
    r.distinct_pages=123u;
    FojStage317RoutingReport saved=r;
    assert(!foj_stage317_sample_atlas(pages,sizes,NAN,.5f,out,&r));
    assert(!foj_stage317_sample_atlas(pages,sizes,.5f,INFINITY,out,&r));
    assert(!foj_stage317_sample_atlas(pages,sizes,-0.001f,.5f,out,&r));
    assert(!foj_stage317_sample_atlas(pages,sizes,.5f,1.001f,out,&r));
    assert(!foj_stage317_sample_atlas(NULL,sizes,.5f,.5f,out,&r));
    assert(!foj_stage317_sample_atlas(pages,NULL,.5f,.5f,out,&r));
    assert(!foj_stage317_sample_atlas(pages,sizes,.5f,.5f,NULL,&r));
    assert(!foj_stage317_sample_atlas(pages,sizes,.5f,.5f,out,NULL));
    size_t wrong[16];memcpy(wrong,sizes,sizeof(wrong));wrong[8]=LEN-1u;
    assert(!foj_stage317_sample_atlas(pages,wrong,.5f,.5f,out,&r));
    const uint8_t *missing[16];memcpy(missing,pages,sizeof(missing));
    missing[13]=NULL;
    assert(!foj_stage317_sample_atlas(missing,sizes,.5f,.5f,out,&r));
    memcpy(missing,pages,sizeof(missing));missing[15]=missing[0];
    assert(!foj_stage317_sample_atlas(missing,sizes,.5f,.5f,out,&r));
    for(unsigned i=0;i<16u;++i) {
        assert(!foj_stage317_sample_atlas(
            pages,sizes,.5f,.5f,owned[i]+4u,&r));
        assert(!foj_stage317_sample_atlas(
            pages,sizes,.5f,.5f,out,
            (FojStage317RoutingReport*)(void*)(owned[i]+4u)));
    }
    assert(!foj_stage317_sample_atlas(
        pages,sizes,.5f,.5f,(uint8_t*)(void*)&r,&r));
    assert(!memcmp(out,old,4u));
    assert(!memcmp(&r,&saved,sizeof(r)));
    for(unsigned i=0;i<16u;++i)
        assert(hash_page(owned[i])==original_hash[i]);
}
int main(void) {
    init();
    nine_intersections();
    straight_edges_and_outer_clamp();
    rejection_and_immutability();
    for(unsigned i=0;i<16u;++i)free(owned[i]);
    puts("STAGE317_NATIVE_16_PAGES_225_CORNER_UVS_CLAMP_FAIL_CLOSED_PASS");
    return 0;
}
