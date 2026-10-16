/* Synthetic 2x2 RGBA image and invented triangles: no game assets. */
#include "textured_triangles.h"
#include <assert.h>
#include <math.h>
#include <stdint.h>
#include <stdio.h>

static void test_uv_and_stride(void) {
    const uint32_t pattern[4]={
        UINT32_C(0xff0000ff),UINT32_C(0xff00ff00),
        UINT32_C(0xffff0000),UINT32_C(0xffffffff)
    };
    FojTexture tex={pattern,2,2,2};
    enum {W=64,H=48,S=70};
    uint32_t pixels[H*S];float z[H*S];
    for(int i=0;i<H*S;++i){pixels[i]=11;z[i]=9;}
    FojRenderSurface target={pixels,z,W,H,S,S};
    FojTextureCamera camera={0,0,0,2.f,0,0,1,0,0};
    FojTexturedVertex tri[3]={
        {-1,-1,0,0,0},{1,-1,0,1,0},{0,1,0,.5f,1}
    };
    size_t count=0;
    assert(foj_textured_render(tri,3,&tex,&target,&camera,&count)==FOJ_TEX_OK);
    assert(count>100);
    assert(pixels[(H/2)*S+W/2]!=UINT32_C(0xff252735));
    assert(z[(H/2)*S+W/2]==0.f);
    for(int y=0;y<H;++y)for(int x=W;x<S;++x){
        assert(pixels[y*S+x]==11);
        assert(z[y*S+x]==9.f);
    }
    assert(pixels[0]==UINT32_C(0xff252735));
}

static void test_depth_and_alpha(void) {
    enum { W=40,H=40 };
    uint32_t pixels[W*H];float z[W*H];
    uint32_t red[1]={UINT32_C(0xff0000ff)};
    uint32_t blue[1]={UINT32_C(0xffff0000)};
    uint32_t clear[1]={0};
    FojTexture rt={red,1,1,1},bt={blue,1,1,1},at={clear,1,1,1};
    FojRenderSurface target={pixels,z,W,H,W,W};
    FojTextureCamera cam={0,0,0,2,0,0,1,0,0};
    FojTexturedVertex overlap[6]={
        {-1,-1,0,0,0},{1,-1,0,1,0},{0,1,0,1,1},
        {-1,-1,1,0,0},{1,-1,1,1,0},{0,1,1,1,1}
    };
    size_t drawn;
    assert(foj_textured_render(overlap,3,&rt,&target,&cam,&drawn)==FOJ_TEX_OK);
    assert(pixels[20*W+20]==red[0]);
    assert(foj_textured_render(overlap+3,3,&bt,&target,&cam,&drawn)==FOJ_TEX_OK);
    assert(pixels[20*W+20]==blue[0]);
    assert(foj_textured_render(overlap+3,3,&at,&target,&cam,&drawn)==FOJ_TEX_OK);
    assert(!drawn&&pixels[20*W+20]==UINT32_C(0xff252735));
    assert(z[20*W+20]==-INFINITY);
    uint32_t pattern[2]={UINT32_C(0xff0000ff),UINT32_C(0xff00ff00)};
    FojTexture mixed={pattern,2,1,2};
    overlap[0].u=overlap[1].u=overlap[2].u=0;
    overlap[3].u=overlap[4].u=overlap[5].u=1;
    assert(foj_textured_render(overlap,6,&mixed,&target,&cam,&drawn)==FOJ_TEX_OK);
    assert(pixels[20*W+20]==pattern[1]);
}

static void test_two_material_sections_and_global_depth(void) {
    enum {W=48,H=48};
    uint32_t pixels[W*H];float depth[W*H];
    const uint32_t red[1]={UINT32_C(0xff0000ff)};
    const uint32_t green[1]={UINT32_C(0xff00ff00)};
    FojTexture tex[2]={{red,1,1,1},{green,1,1,1}};
    FojRenderSurface surface={pixels,depth,W,H,W,W};
    FojTextureCamera cam={0,0,0,2,0,0,1,0,0};
    /* First shape closer (z=1), second further (z=0):
     * the second material must not erase previous depth values. */
    FojTexturedVertex tri[6]={
        {-1,-1,1,0,0},{1,-1,1,1,0},{0,1,1,0,1},
        {-1,-1,0,0,0},{1,-1,0,1,0},{0,1,0,0,1}
    };
    FojTextureSection batches[2]={{0,3,0},{3,3,1}};
    size_t drawn=0;
    assert(foj_textured_render_sections(
        tri,6,tex,2,batches,2,&surface,&cam,&drawn)==FOJ_TEX_OK);
    assert(pixels[24*W+24]==red[0]);
    assert(depth[24*W+24]==1.f);
    assert(drawn>0);
    batches[0].texture_index=1;
    batches[1].texture_index=0;
    assert(foj_textured_render_sections(
        tri,6,tex,2,batches,2,&surface,&cam,&drawn)==FOJ_TEX_OK);
    assert(pixels[24*W+24]==green[0]);
    /* Fail without touching the existing framebuffer. */
    uint32_t previous=pixels[24*W+24];
    batches[1].texture_index=10;
    assert(foj_textured_render_sections(
        tri,6,tex,2,batches,2,&surface,&cam,&drawn)==FOJ_TEX_BOUNDS);
    assert(pixels[24*W+24]==previous);
    batches[1].texture_index=0;
    tri[5].u=NAN;
    assert(foj_textured_render_sections(
        tri,6,tex,2,batches,2,&surface,&cam,&drawn)==FOJ_TEX_GEOMETRY);
    assert(pixels[24*W+24]==previous);
    tri[5].u=0;
    batches[1].first_vertex=2;
    assert(foj_textured_render_sections(
        tri,6,tex,2,batches,2,&surface,&cam,&drawn)==FOJ_TEX_BOUNDS);
}

static void test_bilinear_and_transparent_edge(void) {
    enum {W=42,H=42};
    uint32_t pixels[W*H];float depth[W*H];
    uint32_t color[4]={
        UINT32_C(0xff0000ff),UINT32_C(0xff00ff00),
        UINT32_C(0xffff0000),UINT32_C(0xffffffff)
    };
    FojTexture tex={color,2,2,2};
    FojRenderSurface surface={pixels,depth,W,H,W,W};
    FojTextureCamera cam={0,0,0,2,0,0,1,0,1};
    FojTexturedVertex triangle[3]={
        {-1,-1,0,.5f,.5f},{1,-1,0,.5f,.5f},{0,1,0,.5f,.5f}
    };
    size_t drawn=0;
    assert(foj_textured_render(triangle,3,&tex,&surface,&cam,&drawn)==FOJ_TEX_OK);
    assert(drawn>10);
    assert(pixels[21*W+21]==UINT32_C(0xff808080));
    cam.bilinear=0;
    assert(foj_textured_render(triangle,3,&tex,&surface,&cam,&drawn)==FOJ_TEX_OK);
    assert(pixels[21*W+21]==UINT32_C(0xffffffff));
    /* A transparent red neighbor must NOT bleed a red halo into
     * neighboring opaque blue texels during bilinear interpolation. */
    color[0]=UINT32_C(0x000000ff);
    color[1]=color[2]=color[3]=UINT32_C(0xffff0000);
    cam.bilinear=1;
    assert(foj_textured_render(triangle,3,&tex,&surface,&cam,&drawn)==FOJ_TEX_OK);
    assert(pixels[21*W+21]==UINT32_C(0xffff0000));
    cam.bilinear=2;
    uint32_t previous=pixels[21*W+21];
    assert(foj_textured_render(triangle,3,&tex,&surface,&cam,&drawn)==FOJ_TEX_GEOMETRY);
    assert(pixels[21*W+21]==previous);
}

static void test_malformed_and_degenerate(void) {
    uint32_t colors[16]={0};float z[16]={0};
    uint32_t white[1]={UINT32_C(0xffffffff)};
    FojTexture tex={white,1,1,1};
    FojRenderSurface dest={colors,z,4,4,4,4};
    FojTextureCamera cam={0,0,0,1,0,0,1,0,0};
    FojTexturedVertex tri[3]={
        {0,0,0,0,0},{0,0,0,0,0},{0,0,0,0,0}
    };
    size_t drawn=5;
    assert(foj_textured_render(tri,3,&tex,&dest,&cam,&drawn)==FOJ_TEX_OK);
    assert(!drawn);
    assert(foj_textured_render(tri,2,&tex,&dest,&cam,&drawn)==FOJ_TEX_BOUNDS);
    tri[1].u=NAN;
    assert(foj_textured_render(tri,3,&tex,&dest,&cam,&drawn)==FOJ_TEX_GEOMETRY);
    tri[1].u=0;
    cam.extent=0;
    assert(foj_textured_render(tri,3,&tex,&dest,&cam,&drawn)==FOJ_TEX_GEOMETRY);
    assert(foj_textured_render(NULL,3,&tex,&dest,&cam,&drawn)==FOJ_TEX_ARGUMENT);
}
int main(void) {
    test_uv_and_stride();
    test_depth_and_alpha();
    test_two_material_sections_and_global_depth();
    test_bilinear_and_transparent_edge();
    test_malformed_and_degenerate();
    puts("Textured triangles: UV, depth, alpha, buffer tests passed");
    return 0;
}
