#include "stage305_split_gpu_scene.h"
#include "stage303_bc1_page_uv.h"
#include "bc1_atlas_page.h"
#include <stdint.h>
#include <stdlib.h>
#include <string.h>

enum { SLOT_BYTES=64*64*4, SOURCE_LEN=FOJ_BC1_SOURCE_FILE_BYTES };
static const uint8_t known[3][4]={
    {96,72,201,128}, {232,55,28,128}, {21,202,219,255}
};
static const uint8_t wanted[2][4]={
    {16,199,214,255}, {24,203,222,255}
};
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
static void triangle(FojGpuVertex *dst,
                     float ax,float ay,float bx,float by,float cx,float cy) {
    *dst++=(FojGpuVertex){ax,ay,.55f,1.f,.5f,.5f};
    *dst++=(FojGpuVertex){bx,by,.55f,1.f,.5f,.5f};
    *dst  =(FojGpuVertex){cx,cy,.55f,1.f,.5f,.5f};
}
static void quad(FojGpuVertex *v,float xmin,float xmax) {
    triangle(v,  xmin,-.50f,xmax,-.50f,xmin, .50f);
    triangle(v+3,xmax,-.50f,xmax, .50f,xmin, .50f);
}
int foj_stage305_apply_split_surface(FojGpuPrivateBundleData *b) {
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
            const uint16_t rgb565=(py==1u && px==1u)?0x163au:
                (py==1u && px==2u)?0x1e5bu:0xf800u;
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
        for (size_t i=0;i<FOJ_BC1_PAGE_RGBA_BYTES;i+=4u)
            if (memcmp(page[k]+i,wanted[k],4u))goto done;
    }
    verts=(FojGpuVertex*)calloc(15u,sizeof(FojGpuVertex));
    batches=(FojGpuBatch*)calloc(3u,sizeof(FojGpuBatch));
    if (!verts || !batches)goto done;
    /* Material 0 translucent probe is drawn far from the seam and sampled
     * only outside the audit ROI. Two contiguous quads form one rectangle. */
    triangle(verts,.88f,.88f,.94f,.88f,.88f,.94f);
    quad(verts+3,0.f,.6f);      /* Material 1: right BC1 (2,1) */
    quad(verts+9,-.6f,0.f);     /* Material 2: left BC1 (1,1)  */
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
