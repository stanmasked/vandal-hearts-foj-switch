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
    FojTextureCamera camera={0,0,0,2.f,0,0,1,0};
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
    FojTextureCamera cam={0,0,0,2,0,0,1,0};
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

static void test_malformed_and_degenerate(void) {
    uint32_t colors[16]={0};float z[16]={0};
    uint32_t white[1]={UINT32_C(0xffffffff)};
    FojTexture tex={white,1,1,1};
    FojRenderSurface dest={colors,z,4,4,4,4};
    FojTextureCamera cam={0,0,0,1,0,0,1,0};
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
    test_malformed_and_degenerate();
    puts("Textured triangles: UV, depth, alpha, buffer tests passed");
    return 0;
}
