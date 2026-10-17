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
_Static_assert((size_t)FOJ_GPU_SHADER_MAX_DKSH ==
               (size_t)FOJ_DKSH_MAX_BYTES,
               "DKSH intake and GPU shader slot capacities differ");
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
#if !defined(FOJ_GPU_DRAW_TRIANGLE)
static const FojGpuVertex kResearchTriangle[3]={
    {-0.60f,-0.55f,0.5f,1.0f,0.0f,0.0f},
    { 0.60f,-0.55f,0.5f,1.0f,1.0f,0.0f},
    { 0.00f, 0.65f,0.5f,1.0f,0.5f,1.0f}
};
#endif

int main(int argc,char **argv) {
    (void)argc;(void)argv;
    /* Nonzero exit if setup fails or no frame was presented. */
    int exit_status=3;
    DkDevice device=NULL;
    DkQueue queue=NULL;
    DkCmdBuf cmd=NULL;
    DkSwapchain swapchain=NULL;
    DkMemBlock images_mem[BUFFER_COUNT]={0};
    DkMemBlock cmd_mem=NULL;
    DkMemBlock vertex_mem=NULL;
#if defined(FOJ_GPU_DRAW_TRIANGLE)
    DkMemBlock shader_mem=NULL;
    DkShader shader_vertex={0},shader_fragment={0};
#endif
    DkGpuAddr vertex_gpu_addr=0;
    DkCmdList commands[BUFFER_COUNT][2]={{0}};
    DkImage images[BUFFER_COUNT];
    DkImageView views[BUFFER_COUNT];
    DkImageLayout layout;

    DkDeviceMaker device_maker;
    dkDeviceMakerDefaults(&device_maker);
    /* Keep deko3d's default orientation: clip Z 0..1, framebuffer
     * origin upper-left, clip-space +Y upward. The "PointsUp" choice
     * is represented by zero, not a named bit in some SDK headers. */
    device_maker.flags=DkDeviceFlags_DepthZeroToOne |
                       DkDeviceFlags_OriginUpperLeft;
    device=dkDeviceCreate(&device_maker);
    if (!device) return 2;

    DkQueueMaker queue_maker;
    dkQueueMakerDefaults(&queue_maker,device);
    queue_maker.flags=DkQueueFlags_Graphics;
    queue=dkQueueCreate(&queue_maker);
    if (!queue) goto cleanup;

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

    DkImage const* swap_images[BUFFER_COUNT]={
        &images[0],&images[1]
    };
    DkSwapchainMaker swap_maker;
    dkSwapchainMakerDefaults(&swap_maker,device,nwindowGetDefault(),
                              swap_images,BUFFER_COUNT);
    swapchain=dkSwapchainCreate(&swap_maker);
    if (!swapchain) goto cleanup;

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

    /* The clear-only probe retains its original synthetic triangle.
     * Triangle mode now exercises the actual CPU-to-GPU geometry stream,
     * preparing two invented triangles / one ordered batch. */
#if defined(FOJ_GPU_DRAW_TRIANGLE)
    FojGpuVertex research_vertices[FOJ_RESEARCH_VERTEX_COUNT];
    FojGpuBatch research_batches[FOJ_RESEARCH_BATCH_COUNT];
    FojGpuStreamInfo research_info;
    if (foj_gpu_research_mesh(research_vertices,FOJ_RESEARCH_VERTEX_COUNT,
                              research_batches,FOJ_RESEARCH_BATCH_COUNT,
                              &research_info)!=FOJ_GPU_STREAM_OK ||
        research_info.vertices_written!=FOJ_RESEARCH_VERTEX_COUNT ||
        research_info.batches_written!=FOJ_RESEARCH_BATCH_COUNT ||
        research_batches[0].first_vertex!=0 ||
        research_batches[0].vertex_count!=FOJ_RESEARCH_VERTEX_COUNT)
        goto cleanup;
    const size_t vertex_upload_bytes=sizeof(research_vertices);
#else
    const size_t vertex_upload_bytes=sizeof(kResearchTriangle);
#endif
    uint32_t vertex_memory_bytes=0;
    if (!foj_smoke_image_allocation(vertex_upload_bytes,
                                    DK_MEMBLOCK_ALIGNMENT,
                                    DK_MEMBLOCK_ALIGNMENT,
                                    &vertex_memory_bytes))goto cleanup;
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
    memcpy(vertex_cpu_addr,research_vertices,vertex_upload_bytes);
#else
    memcpy(vertex_cpu_addr,kResearchTriangle,vertex_upload_bytes);
#endif

#if defined(FOJ_GPU_DRAW_TRIANGLE)
    /* Optional native triangle mode. Load UAM-generated research DKSH
     * modules from the user's own SD card, NOT from original PS3 files.
     * This leaves the earlier shader-free GPU clear NRO intact. */
    (void)fsdevMountSdmc();
    DkMemBlockMaker shader_maker;
    dkMemBlockMakerDefaults(&shader_maker,device,
                           FOJ_GPU_SHADER_CODE_POOL);
    shader_maker.flags=DkMemBlockFlags_CpuUncached|
                       DkMemBlockFlags_GpuCached|
                       DkMemBlockFlags_Code;
    shader_mem=dkMemBlockCreate(&shader_maker);
    if (!shader_mem)goto cleanup;
    uint8_t *shader_cpu=(uint8_t*)dkMemBlockGetCpuAddr(shader_mem);
    if (!shader_cpu)goto cleanup;

    size_t vs_bytes=0,fs_bytes=0;
    if (!foj_dksh_read_file(
            "sdmc:/switch/foj/gpu/foj_actor.vert.dksh",
            shader_cpu,FOJ_DKSH_MAX_BYTES,FOJ_DKSH_VERTEX,&vs_bytes))
        goto cleanup;
    if (!foj_dksh_read_file(
            "sdmc:/switch/foj/gpu/foj_triangle.frag.dksh",
            shader_cpu+FOJ_GPU_SHADER_SLOT_BYTES,FOJ_DKSH_MAX_BYTES,
            FOJ_DKSH_FRAGMENT,&fs_bytes))
        goto cleanup;
    FojGpuShaderLayout shader_plan;
    if (!foj_gpu_shader_layout(vs_bytes,fs_bytes,&shader_plan))
        goto cleanup;
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
        dkShaderGetStage(&shader_fragment)!=DkStage_Fragment)
        goto cleanup;
#endif

    /* Mirror switchbrew's deko_basic/Example01 approach: pre-record
     * persistent framebuffer-binding lists, keep command memory alive,
     * and only submit pre-recorded lists during the presentation loop.
     * This avoids reusing/freeing in-flight command memory each frame. */
    DkScissor full_screen={0,0,SCREEN_WIDTH,SCREEN_HEIGHT};
    for (unsigned slot=0;slot<BUFFER_COUNT;++slot) {
        for (unsigned phase=0;phase<2;++phase) {
            DkImageView const* color_targets[]={&views[slot]};
            dkCmdBufBindRenderTargets(cmd,color_targets,1,NULL);
            dkCmdBufSetScissors(cmd,0,&full_screen,1);
            float rgba[4];
            if (!foj_smoke_color(phase,rgba))goto cleanup;
            dkCmdBufClearColorFloat(cmd,0,DkColorMask_RGBA,
                                    rgba[0],rgba[1],rgba[2],rgba[3]);
#if defined(FOJ_GPU_DRAW_TRIANGLE)
            /* This is the first actual GPU triangle DRAW command in source.
             * It requires two valid user-supplied UAM DKSH modules. No FoJ
             * geometry/materials or proprietary assets enter this mode. */
            const DkViewport viewport={0.f,0.f,SCREEN_WIDTH,
                                       SCREEN_HEIGHT,0.f,1.f};
            DkRasterizerState rasterizer;
            DkColorState color_state;
            DkColorWriteState color_write;
            dkRasterizerStateDefaults(&rasterizer);
            dkColorStateDefaults(&color_state);
            dkColorWriteStateDefaults(&color_write);
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
            dkCmdBufBindVtxAttribState(cmd,attribs,2);
            dkCmdBufBindVtxBufferState(cmd,vertex_states,1);
            dkCmdBufBindVtxBuffers(cmd,0,vertex_data,1);
            dkCmdBufDraw(cmd,DkPrimitive_Triangles,
                         (uint32_t)research_info.vertices_written,1,0,0);
#endif
            commands[slot][phase]=dkCmdBufFinishList(cmd);
            if (!commands[slot][phase])goto cleanup;
        }
    }

    padConfigureInput(1,HidNpadStyleSet_NpadStandard);
    PadState pad;
    padInitializeDefault(&pad);
    unsigned frame=0;
    while (appletMainLoop()) {
        padUpdate(&pad);
        if (padGetButtonsDown(&pad)&HidNpadButton_Plus) {
            /* Exiting before presenting a frame is not a successful smoke test. */
            if (frame>0) exit_status=0;
            break;
        }

        const int slot=dkQueueAcquireImage(queue,swapchain);
        if (slot<0 || slot>=BUFFER_COUNT) {
            exit_status=4;
            break;
        }

        /* Immutable GPU command lists, following the official deko3d
         * simple setup example. The clear color alternates periodically. */
        const unsigned palette=foj_smoke_color_for_frame(frame);
        dkQueueSubmitCommands(queue,commands[slot][palette]);
        dkQueuePresentImage(queue,swapchain,slot);
        ++frame;
        exit_status=0;
    }
cleanup:
    if (queue)dkQueueWaitIdle(queue);
    if (cmd)dkCmdBufDestroy(cmd);
    if (vertex_mem)dkMemBlockDestroy(vertex_mem);
#if defined(FOJ_GPU_DRAW_TRIANGLE)
    if (shader_mem)dkMemBlockDestroy(shader_mem);
#endif
    if (cmd_mem)dkMemBlockDestroy(cmd_mem);
    if (swapchain)dkSwapchainDestroy(swapchain);
    for (unsigned i=0;i<BUFFER_COUNT;++i)
        if (images_mem[i])dkMemBlockDestroy(images_mem[i]);
    if (queue)dkQueueDestroy(queue);
    dkDeviceDestroy(device);
    return exit_status;
}
