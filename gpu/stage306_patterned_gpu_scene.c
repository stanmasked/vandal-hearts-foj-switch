#include "stage306_patterned_gpu_scene.h"
#include "stage303_bc1_page_uv.h"
#include "bc1_atlas_page.h"
#include <stdint.h>
#include <stdlib.h>
#include <string.h>

enum { SLOT_BYTES=64*64*4, SOURCE_LEN=FOJ_BC1_SOURCE_FILE_BYTES };
static const uint8_t known[3][4]={
    {96,72,201,128}, {232,55,28,128}, {21,202,219,255}
};
/* Eight independently recognizable horizontal bands, from two adjacent
 * invented BC1 pages. The last band on the left and the first band on the
 * right deliberately have the SAME cyan texels at the page boundary. */
static const uint16_t bands565[2][4]={
    {0xf800u,0xfc00u,0x001fu,0x07ffu},
    {0x07ffu,0xf81fu,0x07e0u,0xffe0u}
};
static void decode565(uint16_t v,uint8_t out[4]) {
    const unsigned r=(v>>11u)&31u,g=(v>>5u)&63u,b=v&31u;
    out[0]=(uint8_t)((r<<3u)|(r>>2u));
    out[1]=(uint8_t)((g<<2u)|(g>>4u));
    out[2]=(uint8_t)((b<<3u)|(b>>2u));
    out[3]=255u;
}
static void put32(uint8_t *p,uint32_t v) {
    p[0]=(uint8_t)v;p[1]=(uint8_t)(v>>8u);
    p[2]=(uint8_t)(v>>16u);p[3]=(uint8_t)(v>>24u);
}
static int valid_original(const FojGpuPrivateBundleData *b) {
    if (!b || !b->vertices || !b->batches ||
        b->report.atlas_count!=3u ||
        b->report.actor.stream.vertices_written!=9u ||
        b->report.actor.stream.batches_written!=3u)return 0;
    for (unsigned i=0;i<3u;++i) {
        if (!b->rgba[i] || b->report.atlas[i].width!=64u ||
            b->report.atlas[i].height!=64u ||
            b->report.atlas[i].pixel_bytes!=SLOT_BYTES ||
            b->batches[i].first_vertex!=3u*i ||
            b->batches[i].vertex_count!=3u ||
            b->batches[i].texture_index!=i)return 0;
        for (size_t j=0;j<SLOT_BYTES;j+=4u)
            if (memcmp(b->rgba[i]+j,known[i],4u))return 0;
    }
    return 1;
}
static void vertex(FojGpuVertex *out,float x,float y,float u,float v) {
    *out=(FojGpuVertex){x,y,.55f,1.f,u,v};
}
static void quad(FojGpuVertex *v,float xmin,float xmax) {
    /* Actual varying UVs: each interpolated page local u goes 0..1 across
     * its half of the shared rectangle (384 physical screen pixels). */
    vertex(v+0,xmin,-.50f,0.f,1.f);
    vertex(v+1,xmax,-.50f,1.f,1.f);
    vertex(v+2,xmin, .50f,0.f,0.f);
    vertex(v+3,xmax,-.50f,1.f,1.f);
    vertex(v+4,xmax, .50f,1.f,0.f);
    vertex(v+5,xmin, .50f,0.f,0.f);
}
int foj_stage306_apply_patterned_split(FojGpuPrivateBundleData *b) {
    if (!valid_original(b))return 0;
    FojBc1PageUv uv[2]={{0}};
    if (!foj_bc1_1024_resolve_uv(511.5f/1024.f,384.5f/1024.f,&uv[0]) ||
        !foj_bc1_1024_resolve_uv(512.5f/1024.f,384.5f/1024.f,&uv[1]) ||
        uv[0].page_x!=1u || uv[1].page_x!=2u ||
        uv[0].page_y!=1u || uv[1].page_y!=1u ||
        uv[0].local_x!=255u || uv[1].local_x!=0u)return 0;

    uint8_t *source=(uint8_t*)malloc(SOURCE_LEN);
    if (!source)return 0;
    memset(source,0,128u);memcpy(source,"DDS ",4u);
    put32(source+4u,124u);put32(source+8u,0x81007u);
    put32(source+12u,1024u);put32(source+16u,1024u);
    put32(source+20u,1024u*1024u/2u);put32(source+28u,1u);
    put32(source+76u,32u);put32(source+80u,4u);
    put32(source+84u,0x31545844u);put32(source+108u,0x1000u);
    for (unsigned by=0;by<256u;++by) {
        for (unsigned bx=0;bx<256u;++bx) {
            const unsigned px=bx/64u,py=by/64u;
            const uint16_t rgb565=(py==1u && (px==1u || px==2u))?
                bands565[px-1u][(bx%64u)/16u]:0xf800u;
            const size_t offset=128u+((size_t)by*256u+bx)*8u;
            source[offset]=(uint8_t)rgb565;
            source[offset+1u]=(uint8_t)(rgb565>>8u);
            source[offset+2u]=0x1fu;source[offset+3u]=0;
            memset(source+offset+4u,0,4u);
        }
    }
    uint8_t *page[2]={NULL,NULL};
    FojAtlasRgba8Info sizes[2]={{0},{0}};
    FojGpuVertex *verts=NULL;
    FojGpuBatch *batches=NULL;
    int ok=0;
    for (unsigned k=0;k<2u;++k) {
        page[k]=(uint8_t*)malloc(FOJ_BC1_PAGE_RGBA_BYTES);
        if (!page[k])goto done;
        if (!foj_bc1_1024_decode_page(
                source,SOURCE_LEN,uv[k].page_x,uv[k].page_y,page[k],
                FOJ_BC1_PAGE_RGBA_BYTES,&sizes[k]) ||
            sizes[k].width!=256u || sizes[k].height!=256u ||
            sizes[k].pixel_bytes!=FOJ_BC1_PAGE_RGBA_BYTES)goto done;
        for (unsigned y=0;y<256u;++y) {
            for (unsigned x=0;x<256u;++x) {
                uint8_t expected[4];
                decode565(bands565[k][x/64u],expected);
                if (memcmp(page[k]+(size_t)(y*256u+x)*4u,expected,4u))
                    goto done;
            }
        }
    }
    verts=(FojGpuVertex*)calloc(15u,sizeof(FojGpuVertex));
    batches=(FojGpuBatch*)calloc(3u,sizeof(FojGpuBatch));
    if (!verts || !batches)goto done;
    /* Material 0 translucent probe is drawn far from the seam and sampled
     * only outside the audit ROI. Two contiguous quads form one rectangle. */
    vertex(verts+0,.88f,.88f,.5f,.5f);
    vertex(verts+1,.94f,.88f,.5f,.5f);
    vertex(verts+2,.88f,.94f,.5f,.5f);
    quad(verts+3,0.f,.6f);      /* Material 1: right patterned BC1 (2,1) */
    quad(verts+9,-.6f,0.f);     /* Material 2: left patterned BC1 (1,1) */
    batches[0]=(FojGpuBatch){0u,3u,0u};
    batches[1]=(FojGpuBatch){3u,6u,1u};
    batches[2]=(FojGpuBatch){9u,6u,2u};
    /* COMMIT: all validations/allocations before touching supplied bundle. */
    free(b->rgba[1]);free(b->rgba[2]);
    free(b->vertices);free(b->batches);
    b->rgba[1]=page[1];b->rgba[2]=page[0];
    b->report.atlas[1]=sizes[1];b->report.atlas[2]=sizes[0];
    b->vertices=verts;b->batches=batches;
    b->report.actor.stream.vertices_written=15u;
    b->report.actor.stream.batches_written=3u;
    page[0]=NULL;page[1]=NULL;verts=NULL;batches=NULL;
    ok=1;
done:
    free(source);free(page[0]);free(page[1]);
    free(verts);free(batches);
    return ok;
}
