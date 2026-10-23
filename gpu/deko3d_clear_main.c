/*
 * FoJ deko3d FIRST-GPU-FRAME research smoke test.
 * This optional, separate NRO clears and presents alternating solid colors
 * *using the GPU*, no original game or material data, no shader binary.
 *
 * Coded against public devkitPro/deko3d C API; toolchain build and runtime
 * on physical Switch MUST be verified. Not part of the nine legacy CPU NROs.
 */
#include <switch.h>
#include <deko3d.h>
#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdio.h>
#include "smoke_plan.h"
#include "deko3d_api_contract.h"
#include "gpu_vertex_stream.h"
#include <string.h>
#if defined(FOJ_GPU_DRAW_TRIANGLE)
#include "dksh_module.h"
#include "shader_layout.h"
#include "research_mesh.h"
#include "gpu_draw_plan.h"
#include "actor_upload_plan.h"
#include "research_texture.h"
#if defined(FOJ_GPU_STAGE329_PATCH_STREAM)
#include "stage328_atomic_corner_patch_stream.h"
#include "stage320_uv_page_batches.h"
#endif
#if defined(FOJ_GPU_NATIVE_ALPHA_ORDER_GUARD)
#include "three_layer_preflight.h"
#endif
#if defined(FOJ_GPU_DYNAMIC_ALPHA_SORT)
#include "transparency_sort.h"
#include "alpha_material_contract.h"
#endif
#if defined(FOJ_GPU_DYNAMIC_PASS_CONTRACT)
#include "alpha_pass_contract.h"
#endif
#include "atlas_dds.h"
#if defined(FOJ_GPU_STAGE302_GENERATED_PAGE_PROBE)
#include "stage302_synthetic_page_probe.h"
#endif
#if defined(FOJ_GPU_STAGE305_SPLIT_SURFACE)
#include "stage305_split_gpu_scene.h"
#endif
#if defined(FOJ_GPU_STAGE306_PATTERNED_SPLIT)
#include "stage306_patterned_gpu_scene.h"
#endif
#if defined(FOJ_GPU_STAGE309_GUTTER_SCENE)
#include "stage309_seam_gutter_scene.h"
#endif
#if defined(FOJ_GPU_STAGE304_UV_NEIGHBOR_PROBE)
#include "stage304_uv_seam_probe.h"
#ifndef FOJ_STAGE304_SIDE
#error "Stage304 requires an explicit left/right compiled selection"
#endif
#if FOJ_STAGE304_SIDE != 0 && FOJ_STAGE304_SIDE != 1
#error "Stage304 only supports left/right of u=0.5"
#endif
#endif
#include "dds_screen_status.h"
#include "dds_command_plan.h"
#include "gpu_boot_diagnostics.h"
#include "gpu_boot_journal.h"
#if defined(FOJ_GPU_PRIVATE_BUNDLE_PREFLIGHT)
#include "private_bundle_intake.h"
#endif
_Static_assert((size_t)FOJ_GPU_SHADER_MAX_DKSH ==
               (size_t)FOJ_DKSH_MAX_BYTES,
               "DKSH intake and GPU shader slot capacities differ");
#if defined(FOJ_GPU_THREE_LAYER_BLEND)
_Static_assert(FOJ_RESEARCH_TEXTURE_COUNT==3,
               "Stage267 requires three independent texture descriptors");
#else
_Static_assert((size_t)FOJ_RESEARCH_MATERIAL_COUNT ==
               (size_t)FOJ_RESEARCH_TEXTURE_COUNT,
               "Synthetic material and texture counts must agree");
#endif
#endif

enum { SCREEN_WIDTH=1280, SCREEN_HEIGHT=720, BUFFER_COUNT=2 };
enum { CMD_MEMORY_SIZE=0x10000 };

/* 24-byte GPU upload format used by original FoJ vertex staging too.
 * The vertices are invented and do not encode commercial game assets.
 */
_Static_assert(sizeof(FojGpuVertex)==24,
               "GPU shader vertex format changed unexpectedly");
_Static_assert(offsetof(FojGpuVertex,x)==0,
               "shader position must start at byte zero");
_Static_assert(offsetof(FojGpuVertex,u)==16,
               "shader UV must start at byte sixteen");
#if defined(FOJ_GPU_STAGE329_PATCH_STREAM)
static uint8_t stage329_pages[4][FOJ_BC1_PAGE_RGBA_BYTES];
static uint8_t stage329_tile[FOJ_STAGE322_TILE_BYTES];
static FojTexturedVertex stage329_cpu_vertices[FOJ_STAGE328_MAX_VERTICES];
static FojTextureSection stage329_sections[FOJ_STAGE328_MAX_SECTIONS];
static FojStage328Receipt stage329_receipt;
static FojGpuVertex stage329_gpu_vertices[FOJ_STAGE328_MAX_VERTICES];
static FojGpuBatch stage329_gpu_batches[FOJ_STAGE328_MAX_SECTIONS];
static FojGpuStreamInfo stage329_gpu_info;

static int stage329_prepare_corner_patch(void) {
    static const uint8_t colors[4][4]={
        {255u,0u,0u,255u},{0u,255u,0u,255u},
        {0u,0u,255u,255u},{255u,255u,255u,255u}
    };
    for(unsigned page=0u;page<4u;++page)
        for(unsigned y=0u;y<256u;++y)
            for(unsigned x=0u;x<256u;++x)
                memcpy(stage329_pages[page]+((size_t)y*256u+x)*4u,
                       colors[page],4u);
    const uint8_t *const pages[4]={
        stage329_pages[0],stage329_pages[1],
        stage329_pages[2],stage329_pages[3]
    };
    const size_t page_lengths[4]={
        FOJ_BC1_PAGE_RGBA_BYTES,FOJ_BC1_PAGE_RGBA_BYTES,
        FOJ_BC1_PAGE_RGBA_BYTES,FOJ_BC1_PAGE_RGBA_BYTES
    };
    /* Keep the synthetic triangle just inside the complete 16x16 tile
     * bounds. Stage327 preserves atlas UVs, so remap tile-section UVs below. */
#if defined(FOJ_GPU_STAGE330_PARTITION_DRAW)
    /* The source triangle fully covers the tile but leaves visible source
     * atlas geometry on all sides. Its junction crosses all four pages. */
    const float u0=480.f/1024.f,v0=480.f/1024.f;
    const float u1=544.f/1024.f,v1=480.f/1024.f;
    const float u2=512.f/1024.f,v2=544.f/1024.f;
#else
    const float u0=504.25f/1024.f,v0=504.25f/1024.f;
    const float u1=519.75f/1024.f,v1=504.25f/1024.f;
    const float u2=512.f/1024.f,v2=519.75f/1024.f;
#endif
    FojStage318Triangle uv_triangle={{{u0,v0},{u1,v1},{u2,v2}}};
    uint16_t ids[1]={0u};
    FojStage320Batch batches[1]={{0}};
    FojStage320Plan plan={0};
    if(!foj_stage320_plan_triangle_batches(
        &uv_triangle,1u,ids,1u,batches,1u,&plan)||
       plan.batch_count!=1u||ids[0]!=0u||batches[0].index_count!=1u)
        return 0;

    FojStage325Triangle triangle={0};
    triangle.point[0]=(FojStage325Vertex){
        (u0-.5f)*200.f,(v0-.5f)*200.f,.5f,u0,v0};
    triangle.point[1]=(FojStage325Vertex){
        (u1-.5f)*200.f,(v1-.5f)*200.f,.5f,u1,v1};
    triangle.point[2]=(FojStage325Vertex){
        (u2-.5f)*200.f,(v2-.5f)*200.f,.5f,u2,v2};
    if(!foj_stage328_prepare_corner_patch_stream(
        batches,&triangle,1u,2u,2u,pages,page_lengths,
        0u,1u,FOJ_RESEARCH_TEXTURE_COUNT,
        stage329_tile,sizeof(stage329_tile),
        stage329_cpu_vertices,FOJ_STAGE328_MAX_VERTICES,
        stage329_sections,FOJ_STAGE328_MAX_SECTIONS,&stage329_receipt))
        return 0;
    static const uint8_t expected_midpoint[4]={128u,128u,128u,255u};
    if(stage329_receipt.atlas_first_x!=504u||
       stage329_receipt.atlas_first_y!=504u||
       stage329_receipt.tile_fnv1a64!=UINT64_C(0xd5565bfb7360b325)||
       memcmp(stage329_receipt.midpoint_rgba,expected_midpoint,4u)||
       stage329_receipt.source_page_mask!=
           (uint16_t)((1u<<5u)|(1u<<6u)|(1u<<9u)|(1u<<10u))||
       stage329_receipt.page_id[0]!=5u||stage329_receipt.page_id[1]!=6u||
       stage329_receipt.page_id[2]!=9u||stage329_receipt.page_id[3]!=10u||
       stage329_receipt.tile_bytes_written!=FOJ_STAGE322_TILE_BYTES||
       stage329_receipt.source_triangles!=1u||
       stage329_receipt.source_texture_index!=0u||
       stage329_receipt.tile_texture_index!=1u)
        return 0;
#if defined(FOJ_GPU_STAGE330_PARTITION_DRAW)
    if(stage329_receipt.output_vertices<9u||
       stage329_receipt.output_vertices>57u||
       stage329_receipt.output_sections!=2u||
       stage329_receipt.tile_fragments!=1u||
       stage329_receipt.remainder_fragments!=1u||
       stage329_receipt.tile_triangles!=2u||
       stage329_receipt.remainder_triangles==0u||
       stage329_receipt.output_vertices!=
           3u*(stage329_receipt.tile_triangles+
               stage329_receipt.remainder_triangles)||
       stage329_sections[0].first_vertex!=0u||
       stage329_sections[0].vertex_count!=
           3u*stage329_receipt.remainder_triangles||
       stage329_sections[0].texture_index!=0u||
       stage329_sections[1].first_vertex!=stage329_sections[0].vertex_count||
       stage329_sections[1].vertex_count!=6u||
       stage329_sections[1].texture_index!=1u)
        return 0;
#else
    if(stage329_receipt.output_vertices!=3u||
       stage329_receipt.output_sections!=1u||
       stage329_receipt.tile_fragments!=1u||
       stage329_receipt.remainder_fragments!=0u||
       stage329_receipt.tile_triangles!=1u||
       stage329_receipt.remainder_triangles!=0u||
       stage329_sections[0].first_vertex!=0u||
       stage329_sections[0].vertex_count!=3u||
       stage329_sections[0].texture_index!=1u)
        return 0;
#endif

    /* Stage324/327 remap only tile-fragment UVs to [0,1]; remainder UVs
     * must remain in atlas coordinates. Never normalize a source remainder twice. */
#if defined(FOJ_GPU_STAGE330_PARTITION_DRAW)
    const size_t source_end=stage329_sections[0].vertex_count;
    for(size_t i=0u;i<source_end;++i) {
        const FojTexturedVertex *const vertex=stage329_cpu_vertices+i;
        if(vertex->u<480.f/1024.f-1e-6f ||
           vertex->u>544.f/1024.f+1e-6f ||
           vertex->v<480.f/1024.f-1e-6f ||
           vertex->v>544.f/1024.f+1e-6f)
            return 0;
    }
    float min_u=1.f,max_u=0.f,min_v=1.f,max_v=0.f;
    for(size_t i=source_end;i<stage329_receipt.output_vertices;++i) {
        const FojTexturedVertex *const vertex=stage329_cpu_vertices+i;
        if(vertex->u<0.f || vertex->u>1.f ||
           vertex->v<0.f || vertex->v>1.f)
            return 0;
        if(vertex->u<min_u)min_u=vertex->u;
        if(vertex->u>max_u)max_u=vertex->u;
        if(vertex->v<min_v)min_v=vertex->v;
        if(vertex->v>max_v)max_v=vertex->v;
    }
    if(min_u>1e-6f||min_v>1e-6f||max_u<.999999f||max_v<.999999f)
        return 0;
#else
    for(size_t i=0u;i<stage329_receipt.output_vertices;++i) {
        const FojTexturedVertex *const vertex=stage329_cpu_vertices+i;
        if(vertex->u<0.f || vertex->u>1.f ||
           vertex->v<0.f || vertex->v>1.f)
            return 0;
    }
#endif
    const FojTextureCamera camera={0.f,0.f,0.f,9.5f,0.f,0.f,1.f,1};
    if(foj_gpu_prepare_stream(
        stage329_cpu_vertices,stage329_receipt.output_vertices,
        stage329_sections,stage329_receipt.output_sections,
        FOJ_RESEARCH_TEXTURE_COUNT,&camera,SCREEN_WIDTH,SCREEN_HEIGHT,
        stage329_gpu_vertices,FOJ_STAGE328_MAX_VERTICES,
        stage329_gpu_batches,FOJ_STAGE328_MAX_SECTIONS,
        &stage329_gpu_info)!=FOJ_GPU_STREAM_OK||
       stage329_gpu_info.vertices_written!=stage329_receipt.output_vertices)
        return 0;
#if defined(FOJ_GPU_STAGE330_PARTITION_DRAW)
    if(stage329_gpu_info.batches_written!=2u||
       stage329_gpu_batches[0].texture_index!=0u||
       stage329_gpu_batches[1].texture_index!=1u)
        return 0;
#else
    if(stage329_gpu_info.batches_written!=1u||
       stage329_gpu_batches[0].texture_index!=1u)
        return 0;
#endif
    return 1;
}
#endif

#if !defined(FOJ_GPU_DRAW_TRIANGLE)
static const FojGpuVertex kResearchTriangle[3]={
    {-0.60f,-0.55f,0.5f,1.0f,0.0f,0.0f},
    { 0.60f,-0.55f,0.5f,1.0f,1.0f,0.0f},
    { 0.00f, 0.65f,0.5f,1.0f,0.5f,1.0f}
};
#endif

#if defined(FOJ_GPU_DRAW_TRIANGLE)
/* Shaderless failure presentation *after* swapchain/command buffers exist,
 * but before DKSH stage setup succeeds. The color stays visible until +
 * or applet exit, while the enclosing NRO still returns a failure code.
 * Device/swapchain/cmd creation failures cannot be displayed here. */
static void foj_present_shader_boot_failure(
    DkQueue queue,DkSwapchain swapchain,DkCmdBuf cmd,
    const DkImageView views[BUFFER_COUNT],FojGpuBootFailure failure) {
    unsigned selected=0;
    float rgba[4];
    if (!foj_gpu_boot_failure_frame(0,0,failure,&selected,rgba))
        return;
    fprintf(stderr,"FoJ GPU boot: %s\n",
            foj_gpu_boot_failure_name(failure));
    const DkScissor full_screen={0,0,SCREEN_WIDTH,SCREEN_HEIGHT};
    DkCmdList lists[BUFFER_COUNT]={0};
    for (unsigned buffer=0;buffer<BUFFER_COUNT;++buffer) {
        DkImageView const *targets[]={&views[buffer]};
        dkCmdBufBindRenderTargets(cmd,targets,1,NULL);
        dkCmdBufSetScissors(cmd,0,&full_screen,1);
        dkCmdBufClearColorFloat(cmd,0,DkColorMask_RGBA,
                                rgba[0],rgba[1],rgba[2],rgba[3]);
        lists[buffer]=dkCmdBufFinishList(cmd);
        if (!lists[buffer])return;
    }
    padConfigureInput(1,HidNpadStyleSet_NpadStandard);
    PadState pad;
    padInitializeDefault(&pad);
    uint64_t frame=0;
    while (appletMainLoop()) {
        padUpdate(&pad);
        if (padGetButtonsDown(&pad)&HidNpadButton_Plus)break;
        const int acquired=dkQueueAcquireImage(queue,swapchain);
        if (acquired<0 || acquired>=BUFFER_COUNT)break;
        float shown_color[4];
        unsigned image=0;
        if (!foj_gpu_boot_failure_frame(frame,(unsigned)acquired,failure,
                                        &image,shown_color))
            break;
        const DkCmdList chosen=lists[image];
        if (!chosen)break;
        dkQueueSubmitCommands(queue,chosen);
        dkQueuePresentImage(queue,swapchain,acquired);
        ++frame;
    }
}
#endif

int main(int argc,char **argv) {
    (void)argc;(void)argv;
#if defined(FOJ_GPU_STAGE329_PATCH_STREAM) && \
    (!defined(FOJ_GPU_DRAW_TRIANGLE) || \
     defined(FOJ_GPU_PRIVATE_ACTOR_DRAW) || \
     defined(FOJ_GPU_PRIVATE_BUNDLE_PREFLIGHT) || \
     defined(FOJ_GPU_THREE_LAYER_BLEND) || \
     defined(FOJ_GPU_ALPHA_BLEND) || defined(FOJ_GPU_DEPTH_PROOF))
#error "Stage329 is a standalone generated-only two-texture patch draw"
#endif
#if defined(FOJ_GPU_DYNAMIC_PASS_CONTRACT) && !defined(FOJ_GPU_DYNAMIC_ALPHA_SORT)
#error "Stage274 GPU pass contract requires Stage273 dynamic alpha sort"
#endif
#if defined(FOJ_GPU_DYNAMIC_ALPHA_SORT) && \
    (!defined(FOJ_GPU_THREE_LAYER_BLEND) || \
     !defined(FOJ_GPU_PRIVATE_ACTOR_DRAW) || \
     !defined(FOJ_GPU_ALPHA_BLEND))
#error "Stage273 dynamic sort requires 3-layer actor and alpha blending"
#endif
#if defined(FOJ_GPU_DYNAMIC_ALPHA_SORT) && defined(FOJ_GPU_NATIVE_ALPHA_ORDER_GUARD)
#error "Dynamic sort is an alternative to Stage270 fixed-order guard"
#endif
#if defined(FOJ_GPU_NEGATIVE_GUEST_RECEIPT) && !defined(FOJ_GPU_NATIVE_ALPHA_ORDER_GUARD)
#error "Stage271 receipt only applies to the opt-in native depth-order guard"
#endif
#if defined(FOJ_GPU_NATIVE_ALPHA_ORDER_GUARD) && !defined(FOJ_GPU_THREE_LAYER_BLEND)
#error "Native transparency guard applies only to opt-in Stage267 three-layer research"
#endif
#if defined(FOJ_GPU_THREE_LAYER_BLEND) && !defined(FOJ_GPU_ALPHA_BLEND)
#error "Stage267 needs Stage265 source-over blending"
#endif
#if defined(FOJ_GPU_THREE_LAYER_BLEND) && !defined(FOJ_GPU_PRIVATE_ACTOR_DRAW)
#error "Stage267 requires validated local generated three-material data"
#endif
#if defined(FOJ_GPU_ALPHA_BLEND) && !defined(FOJ_GPU_DEPTH_PROOF)
#error "GPU alpha blend requires the opt-in depth renderer"
#endif
#if defined(FOJ_GPU_ALPHA_BLEND) && defined(FOJ_GPU_ALPHA_CUTOUT)
#error "Alpha blend and binary cutout are separate research pipelines"
#endif
#if defined(FOJ_GPU_ALPHA_CUTOUT) && !defined(FOJ_GPU_DEPTH_PROOF)
#error "GPU alpha cutout requires the opt-in depth renderer"
#endif
#if defined(FOJ_GPU_DEPTH_PROOF) && !defined(FOJ_GPU_PRIVATE_ACTOR_DRAW)
#error "GPU depth proof requires validated private actor data"
#endif
#if defined(FOJ_GPU_PRIVATE_ACTOR_DRAW) && !defined(FOJ_GPU_PRIVATE_BUNDLE_PREFLIGHT)
#error "Private actor draw must use the fail-closed private intake"
#endif
#if defined(FOJ_GPU_PRIVATE_BUNDLE_PREFLIGHT)
    /* Dedicated opt-in NRO. Validate the entire private actor+material+two
     * DDS set before initializing a GPU device. Never silently render
     * generated fallback as though private intake succeeded. Successful
     * intake still renders *generated quads*, NOT the private actor. */
    (void)fsdevMountSdmc();
    const char *const private_atlases[FOJ_GPU_PRIVATE_REQUIRED_ATLASES]={
        "sdmc:/switch/foj/gpu/material0.dds",
        "sdmc:/switch/foj/gpu/material1.dds",
#if defined(FOJ_GPU_THREE_LAYER_BLEND)
        "sdmc:/switch/foj/gpu/material2.dds",
#endif
    };
    const FojTextureCamera private_camera={
        0.f,0.f,0.f,2.f,0.f,0.f,1.f,0
    };
#if defined(FOJ_GPU_PRIVATE_ACTOR_DRAW)
    FojGpuPrivateBundleData private_payload={0};
    const FojGpuPrivateBundleStatus private_status=
        foj_gpu_private_bundle_load(
            "sdmc:/switch/foj/gpu/actor.fojrm",
            "sdmc:/switch/foj/gpu/actor.fojmat",
            private_atlases,&private_camera,
            SCREEN_WIDTH,SCREEN_HEIGHT,DK_MEMBLOCK_ALIGNMENT,
            &private_payload);
#else
    FojGpuPrivateBundleReport private_report={0};
    const FojGpuPrivateBundleStatus private_status=
        foj_gpu_private_bundle_preflight(
            "sdmc:/switch/foj/gpu/actor.fojrm",
            "sdmc:/switch/foj/gpu/actor.fojmat",
            private_atlases,&private_camera,
            SCREEN_WIDTH,SCREEN_HEIGHT,DK_MEMBLOCK_ALIGNMENT,
            &private_report);
#endif
    if (private_status!=FOJ_PRIVATE_BUNDLE_OK) {
        fprintf(stderr,"FoJ private GPU intake: %s\n",
                foj_gpu_private_bundle_status_name(private_status));
        return 7;
    }
#if defined(FOJ_GPU_STAGE309_GUTTER_SCENE)
#if !defined(FOJ_GPU_PRIVATE_ACTOR_DRAW) || !defined(FOJ_GPU_THREE_LAYER_BLEND)
#error "Stage309 requires the exact generated three-material DDS intake"
#endif
#if defined(FOJ_GPU_DYNAMIC_ALPHA_SORT) || defined(FOJ_GPU_DYNAMIC_PASS_CONTRACT)
#error "Stage309 6/6/6 topology is incompatible with 3/3/3 sort"
#endif
    if (!foj_stage309_prepare_gutter_scene(&private_payload)) {
        fprintf(stderr,"FoJ Stage309 generated BC1 gutter scene refused\n");
        foj_gpu_private_bundle_free(&private_payload);
        return 15;
    }
#if defined(FOJ_GPU_STAGE323_TILE_GUTTER)
#if !defined(FOJ_GPU_STAGE316_CORNER_GUTTER) ||     !defined(FOJ_GPU_STAGE309_GUTTER_SCENE) ||     !defined(FOJ_GPU_STAGE309_LINEAR_GUTTER)
#error "Stage323 requires linear Stage316 synthetic four-page GPU path"
#endif
    FILE *const seam_marker=fopen(
        "sdmc:/switch/foj/gpu/foj-native-stage323-bounded-tile-pass.txt","wx");
#elif defined(FOJ_GPU_STAGE316_CORNER_GUTTER)
#if !defined(FOJ_GPU_STAGE309_GUTTER_SCENE) || !defined(FOJ_GPU_STAGE309_LINEAR_GUTTER)
#error "Stage316 requires the separate linear Stage309 generated three-material path"
#endif
    FILE *const seam_marker=fopen(
        "sdmc:/switch/foj/gpu/foj-native-stage316-four-corner-pass.txt","wx");
#elif defined(FOJ_GPU_STAGE312_HORIZONTAL_GUTTER)
#if !defined(FOJ_GPU_STAGE309_GUTTER_SCENE) || !defined(FOJ_GPU_STAGE309_LINEAR_GUTTER)
#error "Stage312 requires the linear Stage309 native 18-vertex gutter path"
#endif
    FILE *const seam_marker=fopen(
        "sdmc:/switch/foj/gpu/foj-native-stage312-horizontal-gutter-pass.txt","wx");
#elif defined(FOJ_GPU_STAGE310_ROW_PATTERNED_GUTTER)
#if !defined(FOJ_GPU_STAGE309_GUTTER_SCENE)
#error "Stage310 requires Stage309 18-vertex scene infrastructure"
#endif
    FILE *const seam_marker=fopen(
        "sdmc:/switch/foj/gpu/foj-native-stage310-row-gutter-pass.txt","wx");
#else
    FILE *const seam_marker=fopen(
        "sdmc:/switch/foj/gpu/foj-native-stage309-gutter-pass.txt","wx");
#endif
    if (!seam_marker) {
        foj_gpu_private_bundle_free(&private_payload);
        return 15;
    }
#if defined(FOJ_GPU_STAGE323_TILE_GUTTER)
    static const char seam_marker_text[]=
        "FOJ_NATIVE_STAGE323_BOUNDED_TILE_V1 pages=1,1+2,1+1,2+2,2 tile=16x16 bytes=1024 verts=18\n";
#elif defined(FOJ_GPU_STAGE316_CORNER_GUTTER)
    static const char seam_marker_text[]=
        "FOJ_NATIVE_STAGE316_FOUR_CORNER_V1 pages=1,1+2,1+1,2+2,2 colors=4 strict_center=1 verts=18\n";
#elif defined(FOJ_GPU_STAGE312_HORIZONTAL_GUTTER)
    static const char seam_marker_text[]=
        "FOJ_NATIVE_STAGE312_HORIZONTAL_GUTTER_V1 pairs=8 columns=256 strict_mix=256 pages=1,1+1,2 verts=18\n";
#elif defined(FOJ_GPU_STAGE310_ROW_PATTERNED_GUTTER)
    static const char seam_marker_text[]=
        "FOJ_NATIVE_STAGE310_ROW_GUTTER_V1 pairs=8 rows=256 strict_mix=256 pages=1,1+2,1 verts=18\n";
#else
    static const char seam_marker_text[]=
        "FOJ_NATIVE_STAGE309_GUTTER_V1 pages=1,1+2,1 contrast=blue-yellow/red-green verts=18 uv=interpolated\n";
#endif
    const size_t seam_n=fwrite(
        seam_marker_text,1,sizeof(seam_marker_text)-1u,seam_marker);
    const int seam_flushed=fflush(seam_marker);
    const int seam_closed=fclose(seam_marker);
    if (seam_n!=sizeof(seam_marker_text)-1u ||
        seam_flushed || seam_closed) {
        foj_gpu_private_bundle_free(&private_payload);
        return 15;
    }
#endif
#if defined(FOJ_GPU_STAGE306_PATTERNED_SPLIT)
#if !defined(FOJ_GPU_PRIVATE_ACTOR_DRAW) || !defined(FOJ_GPU_THREE_LAYER_BLEND)
#error "Stage306 requires the exact generated three-material intake"
#endif
#if defined(FOJ_GPU_DYNAMIC_ALPHA_SORT) || defined(FOJ_GPU_DYNAMIC_PASS_CONTRACT)
#error "Stage306 3/6/6 geometry is incompatible with Stage273 3/3/3 sort"
#endif
    if (!foj_stage306_apply_patterned_split(&private_payload)) {
        fprintf(stderr,"FoJ Stage306 patterned BC1 UV scene refused\n");
        foj_gpu_private_bundle_free(&private_payload);
        return 14;
    }
    FILE *const pattern_marker=fopen(
        "sdmc:/switch/foj/gpu/foj-native-stage306-pattern-pass.txt","wx");
    if (!pattern_marker) {
        foj_gpu_private_bundle_free(&private_payload);
        return 14;
    }
    static const char pattern_record[]=
        "FOJ_NATIVE_STAGE306_PATTERN_V1 bands=4x2 pages=1,1+2,1 uv=interpolated verts=15\n";
    const size_t pattern_written=fwrite(
        pattern_record,1,sizeof(pattern_record)-1u,pattern_marker);
    const int pattern_flushed=fflush(pattern_marker);
    const int pattern_closed=fclose(pattern_marker);
    if (pattern_written!=sizeof(pattern_record)-1u ||
        pattern_flushed || pattern_closed) {
        foj_gpu_private_bundle_free(&private_payload);
        return 14;
    }
#endif
#if defined(FOJ_GPU_STAGE305_SPLIT_SURFACE)
#if !defined(FOJ_GPU_PRIVATE_ACTOR_DRAW) || !defined(FOJ_GPU_THREE_LAYER_BLEND)
#error "Stage305 requires the exact three synthetic Stage293 material inputs"
#endif
#if defined(FOJ_GPU_DYNAMIC_ALPHA_SORT) || defined(FOJ_GPU_DYNAMIC_PASS_CONTRACT)
#error "Stage305 new 3/6/6 vertex geometry intentionally differs from Stage273 3/3/3 sort"
#endif
    if (!foj_stage305_apply_split_surface(&private_payload)) {
        fprintf(stderr,"FoJ Stage305 generated two-page seam geometry refused\n");
        foj_gpu_private_bundle_free(&private_payload);
        return 13;
    }
    FILE *const two_page_marker=fopen(
        "sdmc:/switch/foj/gpu/foj-native-stage305-split-pass.txt","wx");
    if (!two_page_marker) {
        foj_gpu_private_bundle_free(&private_payload);
        return 13;
    }
    static const char split_text[]=
        "FOJ_NATIVE_STAGE305_SPLIT_V1 left=1,1 right=2,1 uv=511/512 verts=15\n";
    const size_t split_written=fwrite(
        split_text,1,sizeof(split_text)-1u,two_page_marker);
    const int split_flushed=fflush(two_page_marker);
    const int split_closed=fclose(two_page_marker);
    if (split_written!=sizeof(split_text)-1u ||
        split_flushed || split_closed) {
        foj_gpu_private_bundle_free(&private_payload);
        return 13;
    }
#endif
#if defined(FOJ_GPU_STAGE304_UV_NEIGHBOR_PROBE)
#if !defined(FOJ_GPU_PRIVATE_ACTOR_DRAW) || !defined(FOJ_GPU_THREE_LAYER_BLEND)
#error "Stage304 requires actual generated Stage293 three-material intake"
#endif
    FojBc1PageUv page_uv={0};
    if (!foj_stage304_apply_seam_probe(
            &private_payload,FOJ_STAGE304_SIDE,&page_uv)) {
        fprintf(stderr,"FoJ Stage304 generated BC1 seam proof refused\n");
        foj_gpu_private_bundle_free(&private_payload);
        return 12;
    }
    FILE *const seam_receipt=fopen(
        "sdmc:/switch/foj/gpu/foj-native-stage304-seam-pass.txt","wx");
    if (!seam_receipt) {
        foj_gpu_private_bundle_free(&private_payload);
        return 12;
    }
#if FOJ_STAGE304_SIDE == 0
    static const char seam_message[]=
        "FOJ_NATIVE_STAGE304_SEAM_V1 side=left p=1,1 lx=255 ly=128 rgb=16,199,214\n";
#else
    static const char seam_message[]=
        "FOJ_NATIVE_STAGE304_SEAM_V1 side=right p=2,1 lx=0 ly=128 rgb=24,203,222\n";
#endif
    const size_t seam_written=fwrite(
        seam_message,1,sizeof(seam_message)-1u,seam_receipt);
    const int seam_flushed=fflush(seam_receipt);
    const int seam_closed=fclose(seam_receipt);
    if (seam_written!=sizeof(seam_message)-1u ||
        seam_flushed || seam_closed) {
        foj_gpu_private_bundle_free(&private_payload);
        return 12;
    }
#endif
#if defined(FOJ_GPU_STAGE302_GENERATED_PAGE_PROBE)
#if !defined(FOJ_GPU_PRIVATE_ACTOR_DRAW) || !defined(FOJ_GPU_THREE_LAYER_BLEND)
#error "Stage302 requires the actual 3-material research NRO intake"
#endif
    /* Strictly generated-only: refuse any non-Stage293 fixture before
     * replacing rear atlas with a genuine C-decoded 1024 BC1 page.
     * A pre-GPU marker only establishes native CPU execution; the
     * independent NeXium screenshot test proves GPU presentation. */
    if (!foj_stage302_apply_generated_page(&private_payload)) {
        fprintf(stderr,"FoJ Stage302 generated BC1 page refused\n");
        foj_gpu_private_bundle_free(&private_payload);
        return 11;
    }
    FILE *const page_receipt=fopen(
        "sdmc:/switch/foj/gpu/foj-native-stage302-paged-pass.txt","wx");
    if (!page_receipt) {
        foj_gpu_private_bundle_free(&private_payload);
        return 11;
    }
    static const char page_message[]=
        "FOJ_NATIVE_STAGE302_PAGE_V1 p=2,1 rgb=24,203,222 size=256\n";
    const size_t page_written=fwrite(
        page_message,1,sizeof(page_message)-1u,page_receipt);
    const int page_flushed=fflush(page_receipt);
    const int page_closed=fclose(page_receipt);
    if (page_written!=sizeof(page_message)-1u ||
        page_flushed!=0 || page_closed!=0) {
        foj_gpu_private_bundle_free(&private_payload);
        return 11;
    }
#endif
#if defined(FOJ_GPU_DYNAMIC_ALPHA_SORT)
    /* Stage273 research-only dynamic order, computed on the same actor
     * vertex stream submitted to deko3d later. No GPU state exists yet.
     * Require the sole opaque rear material to be the first pass.
     * The other two may appear in either strict back-to-front order.
     * The presumed opaque rear DDS MUST be 255-alpha in every texel. */
    if (private_payload.report.atlas_count!=3u) {
        /* Missing decoded atlas is an invalid bundle, not evidence of
         * a translucent rear pixel. Never issue the alpha-reject marker. */
        fprintf(stderr,"FoJ dynamic alpha sort: incomplete atlas bundle\n");
        foj_gpu_private_bundle_free(&private_payload);
        return 8;
    }
    if (!foj_gpu_opaque_rear_atlas(
            private_payload.rgba[2],&private_payload.report.atlas[2])) {
        fprintf(stderr,"FoJ dynamic alpha sort: non-opaque rear atlas rejected\n");
#if defined(FOJ_GPU_DYNAMIC_PASS_CONTRACT)
        /* Stage274 generated-only negative guest: prove the decoded rear
         * DDS was refused before GPU device creation. Never write source
         * paths or source pixels to the marker. An existing marker cannot
         * be overwritten, and a failed receipt is not proof of refusal. */
        FILE *rear_rejection=fopen(
            "sdmc:/switch/foj/gpu/foj-native-rear-alpha-reject.txt","wx");
        if (!rear_rejection) {
            foj_gpu_private_bundle_free(&private_payload);
            return 9;
        }
        static const char rear_message[]=
            "FOJ_NATIVE_REAR_ALPHA_REJECT_V1 pre_gpu=1\n";
        const size_t rear_written=fwrite(
            rear_message,1,sizeof(rear_message)-1u,rear_rejection);
        const int rear_flushed=fflush(rear_rejection);
        const int rear_closed=fclose(rear_rejection);
        if (rear_written!=sizeof(rear_message)-1u ||
            rear_flushed!=0 || rear_closed!=0) {
            foj_gpu_private_bundle_free(&private_payload);
            return 9;
        }
#endif
        foj_gpu_private_bundle_free(&private_payload);
        return 8;
    }
    uint32_t dynamic_three_passes[3]={UINT32_MAX,UINT32_MAX,UINT32_MAX};
    if (private_payload.report.actor.stream.vertices_written!=9u ||
        private_payload.report.actor.stream.batches_written!=3u ||
        private_payload.batches[0].first_vertex!=0u ||
        private_payload.batches[0].vertex_count!=3u ||
        private_payload.batches[0].texture_index!=0u ||
        private_payload.batches[1].first_vertex!=3u ||
        private_payload.batches[1].vertex_count!=3u ||
        private_payload.batches[1].texture_index!=1u ||
        private_payload.batches[2].first_vertex!=6u ||
        private_payload.batches[2].vertex_count!=3u ||
        private_payload.batches[2].texture_index!=2u) {
        fprintf(stderr,"FoJ dynamic alpha sort: unsupported actor batches\n");
        foj_gpu_private_bundle_free(&private_payload);
        return 8;
    }
    /* Stage275's separate negative guest only attests an actual UNSAFE
     * topology decision on the same GPU-bound projected vertices.
     * A malformed stream, truncated bundle or unsupported sort order
     * must not masquerade as a depth-crossing rejection. */
    const FojAlphaSortStatus dynamic_sort_status=
        foj_alpha_sort_back_to_front(
            private_payload.vertices,3u,dynamic_three_passes,3u);
    if (dynamic_sort_status!=FOJ_ALPHA_SORT_OK) {
        fprintf(stderr,"FoJ dynamic alpha sort: %s\n",
                dynamic_sort_status==FOJ_ALPHA_SORT_UNSAFE?
                "unsafe triangle depth topology":"invalid triangle stream");
#if defined(FOJ_GPU_TOPOLOGY_NEGATIVE_WITNESS)
        if (dynamic_sort_status==FOJ_ALPHA_SORT_UNSAFE) {
            static const char witness[]=
                "FOJ_NATIVE_TOPOLOGY_REJECT_V1 pre_gpu=1 unsafe=1\n";
            FILE *record=fopen(
                "sdmc:/switch/foj/gpu/foj-native-topology-reject.txt","wx");
            if(!record) {
                foj_gpu_private_bundle_free(&private_payload);
                return 9;
            }
            const size_t written=fwrite(witness,1,sizeof(witness)-1u,record);
            const int flushed=fflush(record);
            const int closed=fclose(record);
            if(written!=sizeof(witness)-1u || flushed!=0 || closed!=0) {
                foj_gpu_private_bundle_free(&private_payload);
                return 9;
            }
        }
#endif
        foj_gpu_private_bundle_free(&private_payload);
        return 8;
    }
    if(dynamic_three_passes[0]!=2u) {
        fprintf(stderr,"FoJ dynamic alpha sort: opaque rear not first\n");
        foj_gpu_private_bundle_free(&private_payload);
        return 8;
    }
    fprintf(stderr,"FoJ dynamic alpha sort: pass=%u,%u,%u\n",
            dynamic_three_passes[0],dynamic_three_passes[1],
            dynamic_three_passes[2]);
    /* Stage273 *generated-only diagnostic* binds the actual selected
     * native GPU submission sequence to the subsequent NeXium frames.
     * This must be fresh: never overwrite/follow a prior output marker.
     * No private texture bytes, names or paths are written. */
    FILE *sort_receipt=fopen(
        "sdmc:/switch/foj/gpu/foj-native-sort-pass.txt","wx");
    if (!sort_receipt) {
        foj_gpu_private_bundle_free(&private_payload);
        return 9;
    }
    const int sort_bytes=fprintf(sort_receipt,"FOJ_NATIVE_SORT_V1 %u,%u,%u\n",
        dynamic_three_passes[0],dynamic_three_passes[1],
        dynamic_three_passes[2]);
    const int sort_flushed=fflush(sort_receipt);
    const int sort_closed=fclose(sort_receipt);
    if (sort_bytes!=25 || sort_flushed!=0 || sort_closed!=0) {
        foj_gpu_private_bundle_free(&private_payload);
        return 9;
    }
#endif
#if defined(FOJ_GPU_NATIVE_ALPHA_ORDER_GUARD)
    /* Critical: screen-space geometry is checked on the very same
     * projected/private vertex stream used later for GPU upload.
     * Unsafe or ambiguous overlapping triangles fail BEFORE creating
     * a GPU device, allocating its resources, or issuing draw commands. */
    const FojThreeOrderStatus order_status=foj_three_layer_preflight(
        private_payload.vertices,
        private_payload.report.actor.stream.vertices_written,
        private_payload.batches,
        private_payload.report.actor.stream.batches_written);
    if (order_status!=FOJ_THREE_ORDER_OK) {
        fprintf(stderr,"FoJ native alpha preflight: %s\n",
                order_status==FOJ_THREE_ORDER_UNSAFE?
                "unsafe depth crossing or ordering":"invalid layer geometry");
#if defined(FOJ_GPU_NEGATIVE_GUEST_RECEIPT)
        /* Stage271 opt-in diagnostic, *only* for the generated NeXium
         * rejection test. After geometry validation but BEFORE any GPU
         * device or command list exists, record only the rejection kind.
         * Exclusive creation never follows/overwrites earlier files.
         * A missing receipt makes the guest proof fail closed. */
        if (order_status==FOJ_THREE_ORDER_UNSAFE) {
            FILE *receipt=fopen(
                "sdmc:/switch/foj/gpu/foj-native-unsafe-reject.txt","wx");
            if (receipt) {
                static const char message[]=
                    "FOJ_NATIVE_UNSAFE_REJECT_V1 exit=8 pre_gpu=1\n";
                const size_t written=fwrite(
                    message,1,sizeof(message)-1u,receipt);
                if (written!=sizeof(message)-1u ||
                    fflush(receipt)!=0)
                    fprintf(stderr,"FoJ native rejection receipt I/O failed\n");
                if (fclose(receipt)!=0)
                    fprintf(stderr,"FoJ native rejection receipt close failed\n");
            }
        }
#endif
        foj_gpu_private_bundle_free(&private_payload);
        return 8;
    }
    fprintf(stderr,"FoJ native alpha preflight: safe three-layer ordering\n");
#endif
#if defined(FOJ_GPU_PRIVATE_ACTOR_DRAW)
    fprintf(stderr,"FoJ private actor GPU upload: unverified display\n");
#else
    fprintf(stderr,"FoJ private bundle accepted; synthetic GPU scene\n");
#endif
#endif
    /* Nonzero exit if setup fails or no frame was presented. */
    int exit_status=3;
    DkDevice device=NULL;
    DkQueue queue=NULL;
    DkCmdBuf cmd=NULL;
    DkSwapchain swapchain=NULL;
    DkMemBlock images_mem[BUFFER_COUNT]={0};
#if defined(FOJ_GPU_DEPTH_PROOF)
    DkMemBlock depth_mem[BUFFER_COUNT]={0};
    DkImage depth_images[BUFFER_COUNT];
    DkImageView depth_views[BUFFER_COUNT];
    DkImageLayout depth_layout;
#endif
    DkMemBlock cmd_mem=NULL;
    DkMemBlock vertex_mem=NULL;
#if defined(FOJ_GPU_DRAW_TRIANGLE)
    DkMemBlock shader_mem=NULL;
    DkMemBlock texture_data_mem=NULL;
    DkMemBlock texture_images_mem[FOJ_RESEARCH_TEXTURE_COUNT]={0};
    DkImage texture_images[FOJ_RESEARCH_TEXTURE_COUNT];
    DkImageView texture_views[FOJ_RESEARCH_TEXTURE_COUNT];
    DkGpuAddr texture_data_addr=DK_GPU_ADDR_INVALID;
    DkCmdList dds_status_lists[BUFFER_COUNT][FOJ_RESEARCH_TEXTURE_COUNT]={{0}};
    FojAtlasDdsStatus dds_states[FOJ_RESEARCH_TEXTURE_COUNT]={
        FOJ_ATLAS_DDS_INVALID_ARGUMENT,FOJ_ATLAS_DDS_INVALID_ARGUMENT
    };
    unsigned dds_observed_slots=0;
    int dds_fatal=0;
    FojGpuBootJournal boot_journal={0};
    FojGpuBootStage boot_stage=FOJ_BOOT_DEVICE;
    uint32_t boot_frames=0;
    DkShader shader_vertex={0},shader_fragment={0};
#endif
    DkGpuAddr vertex_gpu_addr=0;
    DkCmdList commands[BUFFER_COUNT][2]={{0}};
    DkImage images[BUFFER_COUNT];
    DkImageView views[BUFFER_COUNT];
    DkImageLayout layout;

#if defined(FOJ_GPU_DRAW_TRIANGLE)
    /* CPU-side checkpoints only; never hardware frame evidence.
     * Logging disables rather than overwriting any prior attempt. */
    (void)fsdevMountSdmc();
    (void)foj_gpu_boot_journal_begin(
        &boot_journal,"sdmc:/switch/foj/gpu/foj-boot-");
#define FOJ_ENTER_BOOT(stage_) do { \
    boot_stage=(stage_); \
    (void)foj_gpu_boot_journal_note(&boot_journal,boot_stage, \
                                    FOJ_BOOT_ENTER,boot_frames); \
} while (0)
#define FOJ_READY_BOOT() do { \
    (void)foj_gpu_boot_journal_note(&boot_journal,boot_stage, \
                                    FOJ_BOOT_READY,boot_frames); \
} while (0)
    FOJ_ENTER_BOOT(FOJ_BOOT_DEVICE);
#endif
    DkDeviceMaker device_maker;
    dkDeviceMakerDefaults(&device_maker);
    /* Keep deko3d's default orientation: clip Z 0..1, framebuffer
     * origin upper-left, clip-space +Y upward. The "PointsUp" choice
     * is represented by zero, not a named bit in some SDK headers. */
    device_maker.flags=DkDeviceFlags_DepthZeroToOne |
                       DkDeviceFlags_OriginUpperLeft;
    device=dkDeviceCreate(&device_maker);
    if (!device) {
#if defined(FOJ_GPU_DRAW_TRIANGLE)
        (void)foj_gpu_boot_journal_note(
            &boot_journal,boot_stage,FOJ_BOOT_FAILED,boot_frames);
        (void)foj_gpu_boot_journal_note(
            &boot_journal,FOJ_BOOT_EXIT,FOJ_BOOT_EXITED,boot_frames);
        foj_gpu_boot_journal_close(&boot_journal);
#endif
#if defined(FOJ_GPU_PRIVATE_ACTOR_DRAW)
        foj_gpu_private_bundle_free(&private_payload);
#endif
        return 2;
    }
#if defined(FOJ_GPU_DRAW_TRIANGLE)
    FOJ_READY_BOOT();
    FOJ_ENTER_BOOT(FOJ_BOOT_QUEUE);
#endif

    DkQueueMaker queue_maker;
    dkQueueMakerDefaults(&queue_maker,device);
    queue_maker.flags=DkQueueFlags_Graphics;
    queue=dkQueueCreate(&queue_maker);
    if (!queue) goto cleanup;
#if defined(FOJ_GPU_DRAW_TRIANGLE)
    FOJ_READY_BOOT();
    FOJ_ENTER_BOOT(FOJ_BOOT_IMAGES);
#endif

    DkImageLayoutMaker layout_maker;
    dkImageLayoutMakerDefaults(&layout_maker,device);
    layout_maker.type=DkImageType_2D;
    layout_maker.format=DkImageFormat_RGBA8_Unorm;
    layout_maker.flags=DkImageFlags_UsageRender|DkImageFlags_UsagePresent;
    layout_maker.dimensions[0]=SCREEN_WIDTH;
    layout_maker.dimensions[1]=SCREEN_HEIGHT;
    layout_maker.dimensions[2]=1;
    dkImageLayoutInitialize(&layout,&layout_maker);
    uint32_t image_bytes=0;
    if (!foj_smoke_image_allocation(dkImageLayoutGetSize(&layout),
                                    dkImageLayoutGetAlignment(&layout),
                                    DK_MEMBLOCK_ALIGNMENT,&image_bytes))
        goto cleanup;

    for (unsigned i=0;i<BUFFER_COUNT;++i) {
        DkMemBlockMaker image_maker;
        dkMemBlockMakerDefaults(&image_maker,device,image_bytes);
        image_maker.flags=DkMemBlockFlags_GpuCached |
                          DkMemBlockFlags_Image;
        images_mem[i]=dkMemBlockCreate(&image_maker);
        if (!images_mem[i]) goto cleanup;
        dkImageInitialize(&images[i],&layout,images_mem[i],0);
        dkImageViewDefaults(&views[i],&images[i]);
    }

#if defined(FOJ_GPU_DRAW_TRIANGLE)
    FOJ_READY_BOOT();
    FOJ_ENTER_BOOT(FOJ_BOOT_SWAPCHAIN);
#endif
#if defined(FOJ_GPU_DEPTH_PROOF)
    /* Separate depth images for each acquired swapchain slot.
     * Deko3d uses 0..1 depth in this NRO. FOJ stream maps nearer
     * camera-space +Z to larger depth; clear 0 and test GREATER.
     * This is a genuine GPU attachment, not a CPU sort of batches. */
    DkImageLayoutMaker depth_layout_maker;
    dkImageLayoutMakerDefaults(&depth_layout_maker,device);
    depth_layout_maker.type=DkImageType_2D;
    depth_layout_maker.format=DkImageFormat_Z24S8;
    depth_layout_maker.flags=DkImageFlags_UsageRender;
    depth_layout_maker.dimensions[0]=SCREEN_WIDTH;
    depth_layout_maker.dimensions[1]=SCREEN_HEIGHT;
    depth_layout_maker.dimensions[2]=1;
    dkImageLayoutInitialize(&depth_layout,&depth_layout_maker);
    uint32_t depth_image_bytes=0;
    if (!foj_smoke_image_allocation(
            dkImageLayoutGetSize(&depth_layout),
            dkImageLayoutGetAlignment(&depth_layout),
            DK_MEMBLOCK_ALIGNMENT,&depth_image_bytes))
        goto cleanup;
    for (unsigned i=0;i<BUFFER_COUNT;++i) {
        DkMemBlockMaker dm;
        dkMemBlockMakerDefaults(&dm,device,depth_image_bytes);
        dm.flags=DkMemBlockFlags_GpuCached|DkMemBlockFlags_Image;
        depth_mem[i]=dkMemBlockCreate(&dm);
        if (!depth_mem[i])goto cleanup;
        dkImageInitialize(&depth_images[i],&depth_layout,depth_mem[i],0);
        dkImageViewDefaults(&depth_views[i],&depth_images[i]);
    }
#endif
    DkImage const* swap_images[BUFFER_COUNT]={
        &images[0],&images[1]
    };
    DkSwapchainMaker swap_maker;
    dkSwapchainMakerDefaults(&swap_maker,device,nwindowGetDefault(),
                              swap_images,BUFFER_COUNT);
    swapchain=dkSwapchainCreate(&swap_maker);
    if (!swapchain) goto cleanup;
#if defined(FOJ_GPU_DRAW_TRIANGLE)
    FOJ_READY_BOOT();
    FOJ_ENTER_BOOT(FOJ_BOOT_COMMAND_BUFFER);
#endif

    DkMemBlockMaker cmd_mem_maker;
    dkMemBlockMakerDefaults(&cmd_mem_maker,device,CMD_MEMORY_SIZE);
    cmd_mem_maker.flags=DkMemBlockFlags_CpuUncached|
                        DkMemBlockFlags_GpuCached;
    cmd_mem=dkMemBlockCreate(&cmd_mem_maker);
    if (!cmd_mem) goto cleanup;
    DkCmdBufMaker cmd_maker;
    dkCmdBufMakerDefaults(&cmd_maker,device);
    cmd=dkCmdBufCreate(&cmd_maker);
    if (!cmd) goto cleanup;
    dkCmdBufAddMemory(cmd,cmd_mem,0,CMD_MEMORY_SIZE);
#if defined(FOJ_GPU_DRAW_TRIANGLE)
    FOJ_READY_BOOT();
    FOJ_ENTER_BOOT(FOJ_BOOT_VERTICES);
#endif

    /* In the default research mode vertices are invented; Stage259 swaps
     * in only validated, retained user-local actor vertices and batches. */
#if defined(FOJ_GPU_DRAW_TRIANGLE)
    FojGpuDrawRange draw_ranges[FOJ_GPU_MAX_BATCHES];
    FojGpuActorUploadPlan actor_upload={0};
    const FojGpuVertex *vertex_source=NULL;
    const FojGpuBatch *batch_source=NULL;
    size_t vertex_count=0u;
    size_t batch_count=0u;
#if defined(FOJ_GPU_STAGE329_PATCH_STREAM)
    if(!stage329_prepare_corner_patch())goto cleanup;
    vertex_source=stage329_gpu_vertices;
    batch_source=stage329_gpu_batches;
    vertex_count=stage329_gpu_info.vertices_written;
    batch_count=stage329_gpu_info.batches_written;
#else
    FojGpuVertex research_vertices[FOJ_RESEARCH_VERTEX_COUNT];
    FojGpuBatch research_batches[FOJ_RESEARCH_BATCH_COUNT];
    FojGpuStreamInfo research_info;
    if (foj_gpu_research_mesh(research_vertices,FOJ_RESEARCH_VERTEX_COUNT,
                              research_batches,FOJ_RESEARCH_BATCH_COUNT,
                              &research_info)!=FOJ_GPU_STREAM_OK)
        goto cleanup;
    vertex_source=research_vertices;
    batch_source=research_batches;
    vertex_count=research_info.vertices_written;
    batch_count=research_info.batches_written;
#if defined(FOJ_GPU_PRIVATE_ACTOR_DRAW)
    vertex_source=private_payload.vertices;
    batch_source=private_payload.batches;
    vertex_count=private_payload.report.actor.stream.vertices_written;
    batch_count=private_payload.report.actor.stream.batches_written;
#endif
#endif
    if (foj_gpu_build_draw_plan(batch_source,batch_count,vertex_count,
                                 FOJ_RESEARCH_TEXTURE_COUNT,
                                 draw_ranges,FOJ_GPU_MAX_BATCHES)!=FOJ_GPU_STREAM_OK ||
        foj_gpu_actor_upload_plan(batch_source,batch_count,vertex_count,
                                  FOJ_RESEARCH_TEXTURE_COUNT,
                                  DK_MEMBLOCK_ALIGNMENT,&actor_upload)!=FOJ_GPU_STREAM_OK ||
        actor_upload.payload_bytes!=vertex_count*sizeof(FojGpuVertex) ||
#if defined(FOJ_GPU_STAGE329_PATCH_STREAM) && \
    defined(FOJ_GPU_STAGE330_PARTITION_DRAW)
        actor_upload.material_mask!=
            ((UINT32_C(1)<<0u)|(UINT32_C(1)<<1u)))
#elif defined(FOJ_GPU_STAGE329_PATCH_STREAM)
        actor_upload.material_mask!=(UINT32_C(1)<<1u))
#else
        actor_upload.material_mask!=
            (UINT32_C(1)<<FOJ_RESEARCH_TEXTURE_COUNT)-1u)
#endif
        goto cleanup;
#if defined(FOJ_GPU_DYNAMIC_PASS_CONTRACT)
    /* Build one validated immutable texture/depth plan for every pass
     * before command-list recording. A contract error submits no GPU draw. */
    FojGpuAlphaPass alpha_passes[FOJ_GPU_ALPHA_PASS_COUNT]={0};
    if (foj_gpu_alpha_pass_contract(
            draw_ranges,batch_count,dynamic_three_passes,3u,
            alpha_passes,FOJ_GPU_ALPHA_PASS_COUNT)!=FOJ_GPU_ALPHA_PASS_OK)
        goto cleanup;
    /* Optional Stage274-only guest evidence. The native code first
     * verifies all texture bindings, alpha flags and depth transitions,
     * then writes a fresh exact descriptor record. This is not a GPU
     * success claim: NeXium must also capture real RGB frames. */
    char native_pass_text[128];
    if (!foj_gpu_alpha_pass_format_receipt(
            alpha_passes,FOJ_GPU_ALPHA_PASS_COUNT,
            native_pass_text,sizeof(native_pass_text)))
        goto cleanup;
    FILE *native_pass_file=fopen(
        "sdmc:/switch/foj/gpu/foj-native-alpha-pass.txt","wx");
    if(!native_pass_file)goto cleanup;
    const size_t pass_len=strlen(native_pass_text);
    const size_t pass_saved=fwrite(native_pass_text,1,pass_len,
                                   native_pass_file);
    const int pass_flushed=fflush(native_pass_file);
    const int pass_closed=fclose(native_pass_file);
    if(pass_saved!=pass_len || pass_flushed!=0 || pass_closed!=0)
        goto cleanup;
#endif
    const size_t vertex_upload_bytes=vertex_count*sizeof(FojGpuVertex);
#else
    const size_t vertex_upload_bytes=sizeof(kResearchTriangle);
#endif
#if defined(FOJ_GPU_DRAW_TRIANGLE)
    /* Validated ordered multi-material draws, with strict buffer capacity. */
    uint32_t vertex_memory_bytes=actor_upload.allocation_bytes;
#else
    uint32_t vertex_memory_bytes=0;
    if (!foj_smoke_image_allocation(vertex_upload_bytes,
                                    DK_MEMBLOCK_ALIGNMENT,
                                    DK_MEMBLOCK_ALIGNMENT,
                                    &vertex_memory_bytes))goto cleanup;
#endif
    DkMemBlockMaker vertex_maker;
    dkMemBlockMakerDefaults(&vertex_maker,device,vertex_memory_bytes);
    vertex_maker.flags=DkMemBlockFlags_CpuUncached|
                       DkMemBlockFlags_GpuCached;
    vertex_mem=dkMemBlockCreate(&vertex_maker);
    if (!vertex_mem)goto cleanup;
    void *vertex_cpu_addr=dkMemBlockGetCpuAddr(vertex_mem);
    vertex_gpu_addr=dkMemBlockGetGpuAddr(vertex_mem);
    /* deko3d uses UINT64_MAX as its INVALID GPU-address sentinel.
     * Zero alone must not be treated as the documented error value. */
    if (!vertex_cpu_addr || vertex_gpu_addr==DK_GPU_ADDR_INVALID)
        goto cleanup;
#if defined(FOJ_GPU_DRAW_TRIANGLE)
    memcpy(vertex_cpu_addr,vertex_source,vertex_upload_bytes);
#else
    memcpy(vertex_cpu_addr,kResearchTriangle,vertex_upload_bytes);
#endif

#if defined(FOJ_GPU_DRAW_TRIANGLE)
    /* Optional native triangle mode. Load UAM-generated research DKSH
     * modules from the user's own SD card, NOT from original PS3 files.
     * This leaves the earlier shader-free GPU clear NRO intact. */
    FOJ_READY_BOOT();
    FOJ_ENTER_BOOT(FOJ_BOOT_SHADERS);
    DkMemBlockMaker shader_maker;
    dkMemBlockMakerDefaults(&shader_maker,device,
                           FOJ_GPU_SHADER_CODE_POOL);
    shader_maker.flags=DkMemBlockFlags_CpuUncached|
                       DkMemBlockFlags_GpuCached|
                       DkMemBlockFlags_Code;
    shader_mem=dkMemBlockCreate(&shader_maker);
    if (!shader_mem) {
        foj_present_shader_boot_failure(
            queue,swapchain,cmd,views,FOJ_GPU_BOOT_SHADER_CODE_MEMORY);
        exit_status=6;
        goto cleanup;
    }
    uint8_t *shader_cpu=(uint8_t*)dkMemBlockGetCpuAddr(shader_mem);
    if (!shader_cpu) {
        foj_present_shader_boot_failure(
            queue,swapchain,cmd,views,FOJ_GPU_BOOT_SHADER_CODE_MEMORY);
        exit_status=6;
        goto cleanup;
    }

    size_t vs_bytes=0,fs_bytes=0;
    if (!foj_dksh_read_file(
            "sdmc:/switch/foj/gpu/foj_actor.vert.dksh",
            shader_cpu,FOJ_DKSH_MAX_BYTES,FOJ_DKSH_VERTEX,&vs_bytes)) {
        foj_present_shader_boot_failure(
            queue,swapchain,cmd,views,FOJ_GPU_BOOT_VERTEX_DKSH);
        exit_status=6;
        goto cleanup;
    }
#if defined(FOJ_GPU_ALPHA_CUTOUT)
    const char *const fragment_path=
        "sdmc:/switch/foj/gpu/foj_alpha_cutout.frag.dksh";
#else
    const char *const fragment_path=
        "sdmc:/switch/foj/gpu/foj_triangle.frag.dksh";
#endif
    if (!foj_dksh_read_file(
            fragment_path,
            shader_cpu+FOJ_GPU_SHADER_SLOT_BYTES,FOJ_DKSH_MAX_BYTES,
            FOJ_DKSH_FRAGMENT,&fs_bytes)) {
        foj_present_shader_boot_failure(
            queue,swapchain,cmd,views,FOJ_GPU_BOOT_FRAGMENT_DKSH);
        exit_status=6;
        goto cleanup;
    }
    FojGpuShaderLayout shader_plan;
    if (!foj_gpu_shader_layout(vs_bytes,fs_bytes,&shader_plan)) {
        foj_present_shader_boot_failure(
            queue,swapchain,cmd,views,FOJ_GPU_BOOT_SHADER_LAYOUT);
        exit_status=6;
        goto cleanup;
    }
    DkShaderMaker shader_init;
    dkShaderMakerDefaults(&shader_init,shader_mem,
                          shader_plan.vertex_offset);
    dkShaderInitialize(&shader_vertex,&shader_init);
    dkShaderMakerDefaults(&shader_init,shader_mem,
                          shader_plan.fragment_offset);
    dkShaderInitialize(&shader_fragment,&shader_init);
    if (!dkShaderIsValid(&shader_vertex) ||
        !dkShaderIsValid(&shader_fragment) ||
        dkShaderGetStage(&shader_vertex)!=DkStage_Vertex ||
        dkShaderGetStage(&shader_fragment)!=DkStage_Fragment) {
        foj_present_shader_boot_failure(
            queue,swapchain,cmd,views,FOJ_GPU_BOOT_SHADER_STAGE);
        exit_status=6;
        goto cleanup;
    }

    FOJ_READY_BOOT();
    FOJ_ENTER_BOOT(FOJ_BOOT_TEXTURES);
    /* Optionally decode private raw RGBA8 or DXT1/DXT5 DDS from SD (8..256 wide,
     * width multiple of 8, up to 256 high); absent files retain invented
     * test gradients. Reject invalid files instead of silently falling back.
     * Each material has its own aligned CPU-visible staging slot. */
    enum {
        #if defined(FOJ_GPU_THREE_LAYER_BLEND)
        TEXTURE_DATA_BYTES=0xD0000,
#else
        TEXTURE_DATA_BYTES=0x90000,
#endif
        IMAGE_DESCRIPTORS_OFFSET=0,
        SAMPLER_DESCRIPTORS_OFFSET=0x100,
        PIXEL_STAGING_OFFSET=0x1000,
        PIXEL_STAGING_STRIDE=0x40000
    };
    _Static_assert(PIXEL_STAGING_OFFSET +
                   FOJ_RESEARCH_TEXTURE_COUNT*PIXEL_STAGING_STRIDE
                   <=TEXTURE_DATA_BYTES, "Texture staging pool too small");
    _Static_assert((size_t)FOJ_ATLAS_MAX_BYTES<=
                   (size_t)PIXEL_STAGING_STRIDE,
                   "Private DDS texture exceeds staging stride");

    DkMemBlockMaker texture_data_maker;
    dkMemBlockMakerDefaults(&texture_data_maker,device,TEXTURE_DATA_BYTES);
    texture_data_maker.flags=DkMemBlockFlags_CpuUncached|
                             DkMemBlockFlags_GpuCached;
    texture_data_mem=dkMemBlockCreate(&texture_data_maker);
    if (!texture_data_mem)goto cleanup;
    uint8_t *texture_data_cpu=(uint8_t*)dkMemBlockGetCpuAddr(texture_data_mem);
    texture_data_addr=dkMemBlockGetGpuAddr(texture_data_mem);
    if (!texture_data_cpu || texture_data_addr==DK_GPU_ADDR_INVALID)
        goto cleanup;

#if !defined(FOJ_GPU_PRIVATE_ACTOR_DRAW) && \
    !defined(FOJ_GPU_STAGE329_PATCH_STREAM)
    const char *const atlas_paths[FOJ_RESEARCH_TEXTURE_COUNT]={
        "sdmc:/switch/foj/gpu/material0.dds",
        "sdmc:/switch/foj/gpu/material1.dds"
    };
#endif
    for (unsigned i=0;i<FOJ_RESEARCH_TEXTURE_COUNT;++i) {
        uint8_t *pixels=texture_data_cpu+PIXEL_STAGING_OFFSET+
                        i*PIXEL_STAGING_STRIDE;
        FojAtlasRgba8Info atlas={0};
        FojAtlasDdsStatus dds_status=FOJ_ATLAS_DDS_INVALID_ARGUMENT;
#if defined(FOJ_GPU_STAGE329_PATCH_STREAM)
        /* Stage329 never reads user DDS files. Slot 0 is an invented fallback;
         * slot 1 is the tile prepared by Stage328 from four generated pages. */
        const int loaded=1;
        dds_status=FOJ_ATLAS_DDS_MISSING;
        if(i==0u) {
#if defined(FOJ_GPU_STAGE330_PARTITION_DRAW)
            /* Synthetic 256x256 atlas: the four quadrants mirror the four
             * generated pages. Its UV=.5 junction matches the 16x16 tile. */
            static const uint8_t source_colors[4][4]={
                {255u,0u,0u,255u},{0u,255u,0u,255u},
                {0u,0u,255u,255u},{255u,255u,255u,255u}
            };
            for(unsigned y=0u;y<256u;++y) {
                for(unsigned x=0u;x<256u;++x) {
                    const unsigned quadrant=(y>=128u?2u:0u)+
                                            (x>=128u?1u:0u);
                    memcpy(pixels+((size_t)y*256u+x)*4u,
                           source_colors[quadrant],4u);
                }
            }
            atlas=(FojAtlasRgba8Info){
                256u,256u,FOJ_BC1_PAGE_RGBA_BYTES};
#else
            if(!foj_research_texture_rgba8(i,pixels,PIXEL_STAGING_STRIDE))
                goto cleanup;
            atlas=(FojAtlasRgba8Info){FOJ_RESEARCH_TEXTURE_WIDTH,
                                      FOJ_RESEARCH_TEXTURE_HEIGHT,
                                      FOJ_RESEARCH_TEXTURE_BYTES};
#endif
        } else if(i==1u) {
            memcpy(pixels,stage329_tile,sizeof(stage329_tile));
            atlas=(FojAtlasRgba8Info){16u,16u,sizeof(stage329_tile)};
        } else {
            goto cleanup;
        }
#elif defined(FOJ_GPU_PRIVATE_ACTOR_DRAW)
        const int loaded=1;
        atlas=private_payload.report.atlas[i];
        if (atlas.pixel_bytes>PIXEL_STAGING_STRIDE)goto cleanup;
        memcpy(pixels,private_payload.rgba[i],atlas.pixel_bytes);
        dds_status=FOJ_ATLAS_DDS_LOADED;
#else
        const int loaded=foj_atlas_dds_try_read_status(
            atlas_paths[i],pixels,PIXEL_STAGING_STRIDE,&atlas,
            &dds_status);
#endif
        /* Generic status and slot ID only: never log user paths, game
         * bytes or file hashes. Console stderr visibility depends on
         * the homebrew environment and is not hardware-verified. */
        fprintf(stderr,"FoJ GPU DDS material %u: %s\n",
                i,foj_atlas_dds_status_name(dds_status));
        dds_states[i]=dds_status;
        dds_observed_slots=i+1u;
        if (loaded<0) {
            /* Preserve a visible GPU failure screen even when intake fails.
             * No partial source bytes are displayed as GPU pixels. */
            dds_fatal=1;
            break;
        }
        if (loaded==0) {
            if (!foj_research_texture_rgba8(i,pixels,
                                            PIXEL_STAGING_STRIDE))
                goto cleanup;
            atlas=(FojAtlasRgba8Info){FOJ_RESEARCH_TEXTURE_WIDTH,
                                      FOJ_RESEARCH_TEXTURE_HEIGHT,
                                      FOJ_RESEARCH_TEXTURE_BYTES};
        }

        DkImageLayout texture_layout;
        DkImageLayoutMaker texture_layout_maker;
        dkImageLayoutMakerDefaults(&texture_layout_maker,device);
        texture_layout_maker.type=DkImageType_2D;
        texture_layout_maker.format=DkImageFormat_RGBA8_Unorm;
        texture_layout_maker.dimensions[0]=atlas.width;
        texture_layout_maker.dimensions[1]=atlas.height;
        texture_layout_maker.dimensions[2]=1;
        dkImageLayoutInitialize(&texture_layout,&texture_layout_maker);
        uint32_t texture_image_bytes=0;
        if (!foj_smoke_image_allocation(
                dkImageLayoutGetSize(&texture_layout),
                dkImageLayoutGetAlignment(&texture_layout),
                DK_MEMBLOCK_ALIGNMENT,&texture_image_bytes))
            goto cleanup;

        DkMemBlockMaker image_maker;
        dkMemBlockMakerDefaults(&image_maker,device,texture_image_bytes);
        image_maker.flags=DkMemBlockFlags_GpuCached|DkMemBlockFlags_Image;
        texture_images_mem[i]=dkMemBlockCreate(&image_maker);
        if (!texture_images_mem[i])goto cleanup;
        dkImageInitialize(&texture_images[i],&texture_layout,
                          texture_images_mem[i],0);
        dkImageViewDefaults(&texture_views[i],&texture_images[i]);
        DkImageDescriptor image_desc;
        dkImageDescriptorInitialize(&image_desc,&texture_views[i],false,false);
        memcpy(texture_data_cpu+IMAGE_DESCRIPTORS_OFFSET+
               i*sizeof(image_desc),&image_desc,sizeof(image_desc));

        /* Decoded destination is always tightly packed RGBA8.
         * Copy row length is in pixels; width multiple-of-8 ensures
         * ensures 32-byte-aligned linear source pitch for RGBA8. */
        const DkCopyBuf source={
            texture_data_addr+PIXEL_STAGING_OFFSET+i*PIXEL_STAGING_STRIDE,
            atlas.width,atlas.height
        };
        const DkImageRect rect={0,0,0,atlas.width,atlas.height,1};
        dkCmdBufCopyBufferToImage(cmd,&source,&texture_views[i],&rect,0);
    }

    if (!dds_fatal) {
    DkSampler sampler;
    dkSamplerDefaults(&sampler);
#if defined(FOJ_GPU_STAGE309_LINEAR_GUTTER)
    sampler.minFilter=DkFilter_Linear;
    sampler.magFilter=DkFilter_Linear;
#endif
#if defined(FOJ_GPU_STAGE307_FILTER)
#if FOJ_GPU_STAGE307_FILTER == 0
    sampler.minFilter=DkFilter_Nearest;
    sampler.magFilter=DkFilter_Nearest;
#elif FOJ_GPU_STAGE307_FILTER == 1
    sampler.minFilter=DkFilter_Linear;
    sampler.magFilter=DkFilter_Linear;
#else
#error "Stage307 only permits explicit nearest=0 or linear=1"
#endif
#endif
    sampler.wrapMode[0]=DkWrapMode_ClampToEdge;
    sampler.wrapMode[1]=DkWrapMode_ClampToEdge;
    DkSamplerDescriptor sampler_desc;
    dkSamplerDescriptorInitialize(&sampler_desc,&sampler);
    memcpy(texture_data_cpu+SAMPLER_DESCRIPTORS_OFFSET,
           &sampler_desc,sizeof(sampler_desc));
#if defined(FOJ_GPU_STAGE307_FILTER)
#if !defined(FOJ_GPU_STAGE306_PATTERNED_SPLIT)
#error "Stage307 filter proof requires exact Stage306 generated patterned pages"
#endif
    /* Guest-authored receipt proves sampler code path, not GPU filtering.
     * Separate live NeXium pixel comparison remains mandatory. */
    FILE *const filter_marker=fopen(
        "sdmc:/switch/foj/gpu/foj-native-stage307-filter-pass.txt","wx");
    if (!filter_marker)goto cleanup;
#if FOJ_GPU_STAGE307_FILTER == 0
    static const char filter_text[]=
        "FOJ_NATIVE_STAGE307_FILTER_V1 mode=nearest mag=nearest min=nearest clamp=edge\n";
#else
    static const char filter_text[]=
        "FOJ_NATIVE_STAGE307_FILTER_V1 mode=linear mag=linear min=linear clamp=edge\n";
#endif
    const size_t filter_written=fwrite(
        filter_text,1,sizeof(filter_text)-1u,filter_marker);
    const int filter_flush=fflush(filter_marker);
    const int filter_close=fclose(filter_marker);
    if (filter_written!=sizeof(filter_text)-1u || filter_flush || filter_close)
        goto cleanup;
#endif

    const DkCmdList upload_list=dkCmdBufFinishList(cmd);
    if (!upload_list)goto cleanup;
    dkQueueSubmitCommands(queue,upload_list);
    dkQueueWaitIdle(queue);
#if defined(FOJ_GPU_STAGE329_PATCH_STREAM)
    /* This receipt attests only that the generated upload command completed.
     * Real framebuffer sampling remains the independent GPU-render proof. */
    char tile_upload_text[384];
#if defined(FOJ_GPU_STAGE330_PARTITION_DRAW)
    const int tile_upload_len=snprintf(
        tile_upload_text,sizeof(tile_upload_text),
        "FOJ_NATIVE_STAGE330_PARTITION_DRAW_UPLOAD_V1 junction=2,2 "
        "tile=16x16 bytes=1024 fnv1a64=%016llx "
        "midpoint=128,128,128,255 vertices=%u sections=2 "
        "source_texture=0 tile_texture=1 remainder_fragments=1 "
        "tile_fragments=1 remainder_triangles=%u tile_triangles=2\n",
        (unsigned long long)stage329_receipt.tile_fnv1a64,
        (unsigned)stage329_receipt.output_vertices,
        (unsigned)stage329_receipt.remainder_triangles);
    const char *const tile_upload_path=
        "sdmc:/switch/foj/gpu/foj-native-stage330-partition-draw-upload.txt";
#else
    const int tile_upload_len=snprintf(
        tile_upload_text,sizeof(tile_upload_text),
        "FOJ_NATIVE_STAGE329_CORNER_PATCH_UPLOAD_V1 junction=2,2 "
        "tile=16x16 bytes=1024 fnv1a64=%016llx "
        "midpoint=128,128,128,255 vertices=3 sections=1 texture=1\n",
        (unsigned long long)stage329_receipt.tile_fnv1a64);
    const char *const tile_upload_path=
        "sdmc:/switch/foj/gpu/foj-native-stage329-corner-patch-upload.txt";
#endif
    if(tile_upload_len<=0||(size_t)tile_upload_len>=sizeof(tile_upload_text))
        goto cleanup;
    FILE *const tile_upload_file=fopen(tile_upload_path,"wx");
    if(!tile_upload_file)goto cleanup;
    const size_t tile_upload_saved=fwrite(
        tile_upload_text,1u,(size_t)tile_upload_len,tile_upload_file);
    const int tile_upload_flushed=fflush(tile_upload_file);
    const int tile_upload_closed=fclose(tile_upload_file);
    if(tile_upload_saved!=(size_t)tile_upload_len||
       tile_upload_flushed!=0||tile_upload_closed!=0)goto cleanup;
#endif
    dkCmdBufClear(cmd);
    } else {
        /* Discard pending copies from earlier slots after DDS failure. */
        dkCmdBufClear(cmd);
    }
#endif

#if defined(FOJ_GPU_DRAW_TRIANGLE)
    /* An invalid DDS remains a failed intake even when we deliberately
     * continue into the shaderless color-only diagnostic path. */
    if (dds_fatal) {
        (void)foj_gpu_boot_journal_note(
            &boot_journal,boot_stage,FOJ_BOOT_FAILED,boot_frames);
    } else {
        FOJ_READY_BOOT();
    }
    FOJ_ENTER_BOOT(FOJ_BOOT_COMMAND_LISTS);
#endif
    /* Mirror switchbrew's deko_basic/Example01 approach: pre-record
     * persistent framebuffer-binding lists, keep command memory alive,
     * and only submit pre-recorded lists during the presentation loop.
     * This avoids reusing/freeing in-flight command memory each frame. */
    DkScissor full_screen={0,0,SCREEN_WIDTH,SCREEN_HEIGHT};
#if defined(FOJ_GPU_DRAW_TRIANGLE)
    /* One persistent shader-free GPU color screen per material and image.
     * These render even when a malformed DDS prevents normal draw lists.
     * Slot 0 appears before slot 1, according to the legend in the docs. */
    for (unsigned buffer=0;buffer<BUFFER_COUNT;++buffer) {
        for (unsigned material=0;material<FOJ_RESEARCH_TEXTURE_COUNT;
             ++material) {
            DkImageView const* targets[]={&views[buffer]};
            float color[4];
            if (!foj_gpu_dds_status_color(dds_states[material],color))
                goto cleanup;
            dkCmdBufBindRenderTargets(cmd,targets,1,NULL);
            dkCmdBufSetScissors(cmd,0,&full_screen,1);
            dkCmdBufClearColorFloat(cmd,0,DkColorMask_RGBA,
                                    color[0],color[1],color[2],color[3]);
            dds_status_lists[buffer][material]=dkCmdBufFinishList(cmd);
            if (!dds_status_lists[buffer][material])goto cleanup;
        }
    }
    if (!dds_fatal) {
#endif
    for (unsigned slot=0;slot<BUFFER_COUNT;++slot) {
        for (unsigned phase=0;phase<2;++phase) {
            DkImageView const* color_targets[]={&views[slot]};
#if defined(FOJ_GPU_DEPTH_PROOF)
            dkCmdBufBindRenderTargets(cmd,color_targets,1,&depth_views[slot]);
#else
            dkCmdBufBindRenderTargets(cmd,color_targets,1,NULL);
#endif
            dkCmdBufSetScissors(cmd,0,&full_screen,1);
#if defined(FOJ_GPU_DEPTH_PROOF)
            /* Clear on EVERY phase/list so prior frames cannot occlude
             * later frames when swapchain images are reacquired. */
            dkCmdBufClearDepthStencil(cmd,true,0.0f,0,0);
#endif
            float rgba[4];
            if (!foj_smoke_color(phase,rgba))goto cleanup;
            dkCmdBufClearColorFloat(cmd,0,DkColorMask_RGBA,
                                    rgba[0],rgba[1],rgba[2],rgba[3]);
#if defined(FOJ_GPU_DRAW_TRIANGLE)
            /* Each validated draw range selects its own GPU texture,
             * optionally sourced from a user-owned local RGBA8 DDS atlas. */
            const DkViewport viewport={0.f,0.f,SCREEN_WIDTH,
                                       SCREEN_HEIGHT,0.f,1.f};
            DkRasterizerState rasterizer;
            DkColorState color_state;
            DkColorWriteState color_write;
            dkRasterizerStateDefaults(&rasterizer);
            dkColorStateDefaults(&color_state);
            dkColorWriteStateDefaults(&color_write);
#if defined(FOJ_GPU_ALPHA_BLEND)
            DkBlendState alpha_blend;
            dkBlendStateDefaults(&alpha_blend);
            /* SrcAlpha / (1-SrcAlpha) standard straight-alpha RGB.
             * Front translucent batches must be submitted AFTER opaque
             * rear geometry, with depth test ON and depth write OFF. */
            dkColorStateSetBlendEnable(&color_state,0,false);
#endif
#if defined(FOJ_GPU_DEPTH_PROOF)
            DkDepthStencilState depth_state;
            dkDepthStencilStateDefaults(&depth_state);
            depth_state.depthTestEnable=true;
            depth_state.depthWriteEnable=true;
            depth_state.depthCompareOp=DkCompareOp_Greater;
#endif
            DkShader const* shaders[2]={
                &shader_vertex,&shader_fragment
            };
            /* Named bitfields avoid accidental association of an
             * unnamed padding bit with the shader's vertex layout. */
            const DkVtxAttribState attribs[2]={
                {
                    .bufferId=0, .isFixed=0, .offset=0,
                    .size=DkVtxAttribSize_4x32,
                    .type=DkVtxAttribType_Float, .isBgra=0
                },
                {
                    .bufferId=0, .isFixed=0,
                    .offset=offsetof(FojGpuVertex,u),
                    .size=DkVtxAttribSize_2x32,
                    .type=DkVtxAttribType_Float, .isBgra=0
                }
            };
            const DkVtxBufferState vertex_states[1]={
                { .stride=sizeof(FojGpuVertex), .divisor=0 }
            };
            const DkBufExtents vertex_data[1]={
                { .addr=vertex_gpu_addr,
                  .size=vertex_upload_bytes }
            };
            dkCmdBufSetViewports(cmd,0,&viewport,1);
            dkCmdBufBindShaders(cmd,DkStageFlag_GraphicsMask,shaders,2);
            dkCmdBufBindRasterizerState(cmd,&rasterizer);
            dkCmdBufBindColorState(cmd,&color_state);
            dkCmdBufBindColorWriteState(cmd,&color_write);
#if defined(FOJ_GPU_DEPTH_PROOF)
            dkCmdBufBindDepthStencilState(cmd,&depth_state);
#endif
            dkCmdBufBindVtxAttribState(cmd,attribs,2);
            dkCmdBufBindVtxBufferState(cmd,vertex_states,1);
            dkCmdBufBindVtxBuffers(cmd,0,vertex_data,1);
            dkCmdBufBindImageDescriptorSet(cmd,
                  texture_data_addr+IMAGE_DESCRIPTORS_OFFSET,
                  FOJ_RESEARCH_TEXTURE_COUNT);
            dkCmdBufBindSamplerDescriptorSet(cmd,
                  texture_data_addr+SAMPLER_DESCRIPTORS_OFFSET,1);
#if defined(FOJ_GPU_ALPHA_BLEND)
            /* Exactly two validated ordered sections, warm material 0 in
             * front and cool 1 behind. Render opaque cool first, then
             * translucent warm: blending is deliberately NOT commutative.
             * This is only the generated 2-material experiment. */
#if defined(FOJ_GPU_THREE_LAYER_BLEND)
            /* Three invented draw ranges are input-ordered violet(0),
             * warm(1), cool(2). GPU submission MUST be opaque cool,
             * then warm middle, then violet nearest (back to front). */
            if (batch_count!=3u ||
                draw_ranges[0].material_index!=0u ||
                draw_ranges[1].material_index!=1u ||
                draw_ranges[2].material_index!=2u)
                goto cleanup;
#if defined(FOJ_GPU_DYNAMIC_ALPHA_SORT)
            const uint32_t *const pass_order=dynamic_three_passes;
#else
            const size_t pass_order[3]={2u,1u,0u};
#endif
#else
            if (batch_count!=2u ||
                draw_ranges[0].material_index!=0u ||
                draw_ranges[1].material_index!=1u)
                goto cleanup;
            const size_t pass_order[2]={1u,0u};
#endif
            for (size_t pass=0;pass<FOJ_RESEARCH_TEXTURE_COUNT;++pass) {
                const FojGpuDrawRange *range=&draw_ranges[pass_order[pass]];
#if defined(FOJ_GPU_DYNAMIC_PASS_CONTRACT)
                const FojGpuAlphaPass *planned=&alpha_passes[pass];
                if (range->material_index!=planned->material_index ||
                    range->first_vertex!=planned->first_vertex ||
                    range->vertex_count!=planned->vertex_count)
                    goto cleanup;
                const bool translucent=planned->blend_enabled!=0u;
#else
#if defined(FOJ_GPU_THREE_LAYER_BLEND)
                const bool translucent=range->material_index!=2u;
#else
                const bool translucent=range->material_index==0u;
#endif
#endif
                DkColorState pass_color=color_state;
                dkColorStateSetBlendEnable(&pass_color,0,translucent);
                dkCmdBufBindColorState(cmd,&pass_color);
                if (translucent)
                    dkCmdBufBindBlendStates(cmd,0,&alpha_blend,1);
                DkDepthStencilState pass_depth=depth_state;
#if defined(FOJ_GPU_DYNAMIC_PASS_CONTRACT)
                pass_depth.depthTestEnable=planned->depth_test_enabled!=0u;
                pass_depth.depthWriteEnable=planned->depth_write_enabled!=0u;
#else
                pass_depth.depthWriteEnable=!translucent;
#endif
                dkCmdBufBindDepthStencilState(cmd,&pass_depth);
#if defined(FOJ_GPU_DYNAMIC_PASS_CONTRACT)
                DkResHandle handle=dkMakeTextureHandle(planned->material_index,0);
#else
                DkResHandle handle=dkMakeTextureHandle(range->material_index,0);
#endif
                dkCmdBufBindTextures(cmd,DkStage_Fragment,0,&handle,1);
#if defined(FOJ_GPU_DYNAMIC_PASS_CONTRACT)
                dkCmdBufDraw(cmd,DkPrimitive_Triangles,
                             planned->vertex_count,1,planned->first_vertex,0);
#else
                dkCmdBufDraw(cmd,DkPrimitive_Triangles,
                             range->vertex_count,1,range->first_vertex,0);
#endif
            }
#else
            for (size_t batch=0;batch<batch_count;
                 ++batch) {
                const FojGpuDrawRange *range=&draw_ranges[batch];
                DkResHandle handle=dkMakeTextureHandle(range->material_index,0);
                dkCmdBufBindTextures(cmd,DkStage_Fragment,0,&handle,1);
                dkCmdBufDraw(cmd,DkPrimitive_Triangles,
                             range->vertex_count,1,range->first_vertex,0);
            }
#endif
#endif
            commands[slot][phase]=dkCmdBufFinishList(cmd);
            if (!commands[slot][phase])goto cleanup;
        }
    }

#if defined(FOJ_GPU_DRAW_TRIANGLE)
    }
#endif
#if defined(FOJ_GPU_DRAW_TRIANGLE)
    FOJ_READY_BOOT();
    FOJ_ENTER_BOOT(FOJ_BOOT_PRESENT);
#endif
    padConfigureInput(1,HidNpadStyleSet_NpadStandard);
    PadState pad;
    padInitializeDefault(&pad);
    unsigned frame=0;
    while (appletMainLoop()) {
        padUpdate(&pad);
        if (padGetButtonsDown(&pad)&HidNpadButton_Plus) {
            /* Exiting before presenting a frame is not a successful smoke test. */
            if (frame>0) {
#if defined(FOJ_GPU_DRAW_TRIANGLE)
                exit_status=dds_fatal?5:0;
#else
                exit_status=0;
#endif
            }
            break;
        }

        const int slot=dkQueueAcquireImage(queue,swapchain);
        if (slot<0 || slot>=BUFFER_COUNT) {
            exit_status=4;
            break;
        }

        /* Immutable GPU command lists, following the official deko3d
         * simple setup example. The clear color alternates periodically. */
#if defined(FOJ_GPU_DRAW_TRIANGLE)
        /* The same checked command planner is exercised by the SDK-free
         * host simulation: never submit a scene list after a fatal DDS,
         * select only the actual acquired framebuffer's lists, and keep
         * the first 120 frames of each observed material in order. */
#if defined(FOJ_GPU_THREE_LAYER_BLEND)
        /* Three-slot diagnostics are isolated from the legacy two-slot
         * host planner. Keep a failed final slot visibly displayed. */
        const unsigned status_frames=FOJ_GPU_DDS_STATUS_FRAMES_PER_SLOT;
        const int show_status=dds_fatal ||
                             frame<3u*status_frames;
        const unsigned status_index=dds_fatal?
            dds_observed_slots-1u : frame/status_frames;
        if (show_status && status_index>=FOJ_RESEARCH_TEXTURE_COUNT) {
            exit_status=5;
            break;
        }
        const DkCmdList chosen=show_status?
            dds_status_lists[slot][status_index]:
            commands[slot][foj_smoke_color_for_frame(frame)];
#else
        FojGpuDdsFrameCommand plan={0};
        if (!foj_gpu_dds_frame_command(frame,(unsigned)slot,dds_states,
                                       dds_observed_slots,dds_fatal,&plan)) {
            exit_status=5;
            break;
        }
        const DkCmdList chosen=
            plan.kind==FOJ_GPU_DDS_LIST_STATUS?
            dds_status_lists[plan.buffer][plan.index]:
            commands[plan.buffer][plan.index];
#endif
        if (!chosen) { exit_status=5; break; }
        dkQueueSubmitCommands(queue,chosen);
#else
        const unsigned palette=foj_smoke_color_for_frame(frame);
        dkQueueSubmitCommands(queue,commands[slot][palette]);
#endif
        dkQueuePresentImage(queue,swapchain,slot);
        ++frame;
#if defined(FOJ_GPU_DRAW_TRIANGLE)
        ++boot_frames;
        exit_status=dds_fatal?5:0;
#else
        exit_status=0;
#endif
    }
cleanup:
#if defined(FOJ_GPU_DRAW_TRIANGLE)
    (void)foj_gpu_boot_journal_note(
        &boot_journal,boot_stage,
        exit_status?FOJ_BOOT_FAILED:FOJ_BOOT_READY,boot_frames);
    (void)foj_gpu_boot_journal_note(
        &boot_journal,FOJ_BOOT_EXIT,FOJ_BOOT_EXITED,boot_frames);
    foj_gpu_boot_journal_close(&boot_journal);
#endif
    if (queue)dkQueueWaitIdle(queue);
    if (cmd)dkCmdBufDestroy(cmd);
    if (vertex_mem)dkMemBlockDestroy(vertex_mem);
#if defined(FOJ_GPU_DRAW_TRIANGLE)
    if (shader_mem)dkMemBlockDestroy(shader_mem);
    for (unsigned i=0;i<FOJ_RESEARCH_TEXTURE_COUNT;++i)
        if (texture_images_mem[i])dkMemBlockDestroy(texture_images_mem[i]);
    if (texture_data_mem)dkMemBlockDestroy(texture_data_mem);
#endif
    if (cmd_mem)dkMemBlockDestroy(cmd_mem);
    if (swapchain)dkSwapchainDestroy(swapchain);
#if defined(FOJ_GPU_DEPTH_PROOF)
    for (unsigned i=0;i<BUFFER_COUNT;++i)
        if (depth_mem[i])dkMemBlockDestroy(depth_mem[i]);
#endif
    for (unsigned i=0;i<BUFFER_COUNT;++i)
        if (images_mem[i])dkMemBlockDestroy(images_mem[i]);
    if (queue)dkQueueDestroy(queue);
    dkDeviceDestroy(device);
#if defined(FOJ_GPU_PRIVATE_ACTOR_DRAW)
    foj_gpu_private_bundle_free(&private_payload);
#endif
    return exit_status;
}
