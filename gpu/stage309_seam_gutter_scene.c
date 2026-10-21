#include "stage309_seam_gutter_scene.h"
#include "stage308_cross_page_bilinear.h"
#include "bc1_atlas_page.h"
#include <stdint.h>
#include <stdlib.h>
#include <string.h>

enum { IN_LEN=64*64*4, BC1_LEN=FOJ_BC1_SOURCE_FILE_BYTES };
static const uint8_t fixture_color[3][4]={
    {96,72,201,128},{232,55,28,128},{21,202,219,255}
};
static int valid_source(const FojGpuPrivateBundleData *b) {
    if (!b || !b->vertices || !b->batches ||
        b->report.atlas_count!=3u ||
        b->report.actor.stream.vertices_written!=9u ||
        b->report.actor.stream.batches_written!=3u)return 0;
    for (unsigned i=0;i<3u;++i) {
        if (!b->rgba[i] || b->report.atlas[i].width!=64u ||
            b->report.atlas[i].height!=64u ||
            b->report.atlas[i].pixel_bytes!=IN_LEN ||
            b->batches[i].texture_index!=i ||
            b->batches[i].first_vertex!=i*3u ||
            b->batches[i].vertex_count!=3u)return 0;
        for (size_t j=0;j<IN_LEN;j+=4u)
            if (memcmp(b->rgba[i]+j,fixture_color[i],4u))return 0;
    }
    return 1;
}
static void put32(uint8_t *dst,unsigned n) {
    dst[0]=(uint8_t)n;dst[1]=(uint8_t)(n>>8u);
    dst[2]=(uint8_t)(n>>16u);dst[3]=(uint8_t)(n>>24u);
}
static void vertex(FojGpuVertex *out,float x,float y,float z,float u,float v) {
    *out=(FojGpuVertex){x,y,z,1.f,u,v};
}
static void rect(FojGpuVertex *out,float x0,float x1,float z,
                 float u0,float u1) {
    vertex(out+0,x0,-.5f,z,u0,1.f);
    vertex(out+1,x1,-.5f,z,u1,1.f);
    vertex(out+2,x0, .5f,z,u0,0.f);
    vertex(out+3,x1,-.5f,z,u1,1.f);
    vertex(out+4,x1, .5f,z,u1,0.f);
    vertex(out+5,x0, .5f,z,u0,0.f);
}
int foj_stage309_prepare_gutter_scene(FojGpuPrivateBundleData *b) {
    if (!valid_source(b))return 0;
    uint8_t *src=(uint8_t*)calloc(BC1_LEN,1u);
    if (!src)return 0;
    memcpy(src,"DDS ",4u);
    put32(src+4u,124u);put32(src+8u,0x81007u);
    put32(src+12u,1024u);put32(src+16u,1024u);
    put32(src+20u,1024u*1024u/2u);put32(src+28u,1u);
    put32(src+76u,32u);put32(src+80u,4u);
    put32(src+84u,0x31545844u);put32(src+108u,0x1000u);

    /* Full synthetic 1024 atlas; page (1,1) blue/red from top to
     * bottom, page (2,1) yellow/green. All other pages black. */
    for (unsigned block_y=0;block_y<256u;++block_y) {
        for (unsigned block_x=0;block_x<256u;++block_x) {
            const unsigned px=block_x/64u,py=block_y/64u;
            const int bottom=(block_y%64u)>=32u;
            const uint16_t color=(py==1u && px==1u)?
                (uint16_t)(bottom?0xf800u:0x001fu):
                (py==1u && px==2u)?
                (uint16_t)(bottom?0x07e0u:0xffe0u):0u;
            const size_t at=128u+((size_t)block_y*256u+block_x)*8u;
            src[at]=(uint8_t)color;src[at+1]=(uint8_t)(color>>8u);
            /* BC1 palette index zero throughout every 4x4 block. */
            src[at+2]=0u;src[at+3]=0u;
        }
    }
    uint8_t *left=NULL,*right=NULL,*bridge=NULL;
    FojGpuVertex *verts=NULL;FojGpuBatch *batches=NULL;
    FojAtlasRgba8Info left_meta={0},right_meta={0};
    int success=0;
    left=(uint8_t*)malloc(FOJ_BC1_PAGE_RGBA_BYTES);
    right=(uint8_t*)malloc(FOJ_BC1_PAGE_RGBA_BYTES);
    bridge=(uint8_t*)malloc(FOJ_BC1_PAGE_RGBA_BYTES);
    if (!left || !right || !bridge)goto end;
    if (!foj_bc1_1024_decode_page(src,BC1_LEN,1u,1u,left,
            FOJ_BC1_PAGE_RGBA_BYTES,&left_meta) ||
        !foj_bc1_1024_decode_page(src,BC1_LEN,2u,1u,right,
            FOJ_BC1_PAGE_RGBA_BYTES,&right_meta) ||
        left_meta.width!=256u || left_meta.height!=256u ||
        left_meta.pixel_bytes!=FOJ_BC1_PAGE_RGBA_BYTES ||
        right_meta.width!=256u || right_meta.height!=256u ||
        right_meta.pixel_bytes!=FOJ_BC1_PAGE_RGBA_BYTES)goto end;
    const uint8_t blue[4]={0,0,255,255};
    const uint8_t yellow[4]={255,255,0,255};
    const uint8_t red[4]={255,0,0,255};
    const uint8_t green[4]={0,255,0,255};
    for (unsigned y=0;y<256u;++y) {
        const uint8_t *l=(y<128u)?blue:red;
        const uint8_t *r=(y<128u)?yellow:green;
        uint8_t middle[4];
        if (memcmp(left+((size_t)y*256u+255u)*4u,l,4u) ||
            memcmp(right+((size_t)y*256u)*4u,r,4u) ||
            !foj_stage308_cross_page_bilinear(
                left,FOJ_BC1_PAGE_RGBA_BYTES,
                right,FOJ_BC1_PAGE_RGBA_BYTES,y,.5f,middle) ||
            !foj_stage308_requires_two_pages(l,r,middle))goto end;
        /* The seam third material carries two true edge texels meeting
         * at U=0.5. Native linear interpolation gives the Stage308
         * midpoint at the center of this narrow GPU quad. */
        for (unsigned x=0;x<256u;++x) {
            const uint8_t *source=x<128u?l:r;
            memcpy(bridge+((size_t)y*256u+x)*4u,source,4u);
        }
    }
    verts=(FojGpuVertex*)calloc(18u,sizeof(FojGpuVertex));
    batches=(FojGpuBatch*)calloc(3u,sizeof(FojGpuBatch));
    if (!verts || !batches)goto end;
    /* Draw 2 original pages first, then a narrow foreground gutter
     * patch that reconstructs both page-edge texels with GPU linear
     * filtering. It is intentionally an explicit layout choice. */
    rect(verts+0,-.03f,.03f,.68f,127.5f/256.f,128.5f/256.f);
    rect(verts+6,0.f,.6f,.55f,.5f,.5f);
    rect(verts+12,-.6f,0.f,.55f,.5f,.5f);
    batches[0]=(FojGpuBatch){0u,6u,0u};
    batches[1]=(FojGpuBatch){6u,6u,1u};
    batches[2]=(FojGpuBatch){12u,6u,2u};
    /* Transactional release+commit: no partial change on failure. */
    for (unsigned i=0;i<3u;++i)free(b->rgba[i]);
    free(b->vertices);free(b->batches);
    b->rgba[0]=bridge;b->rgba[1]=right;b->rgba[2]=left;
    b->report.atlas[0]=(FojAtlasRgba8Info){256u,256u,FOJ_BC1_PAGE_RGBA_BYTES};
    b->report.atlas[1]=right_meta;b->report.atlas[2]=left_meta;
    b->vertices=verts;b->batches=batches;
    b->report.actor.stream.vertices_written=18u;
    b->report.actor.stream.batches_written=3u;
    bridge=NULL;left=NULL;right=NULL;verts=NULL;batches=NULL;
    success=1;
end:
    free(src);free(left);free(right);free(bridge);
    free(verts);free(batches);
    return success;
}
