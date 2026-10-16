/*
 * FoJ deko3d FIRST-GPU-FRAME research smoke test.
 * This optional, separate NRO clears and presents a changing solid color
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

enum { SCREEN_WIDTH=1280, SCREEN_HEIGHT=720, BUFFER_COUNT=2 };
enum { CMD_MEMORY_SIZE=0x10000 };

static uint32_t round_up(uint64_t bytes, uint32_t alignment) {
    /* Intended for bounded RGBA8 1280x720 image layouts only. */
    if (!alignment || bytes > UINT32_MAX-(uint64_t)alignment) return 0;
    return (uint32_t)((bytes + alignment-1) & ~(uint64_t)(alignment-1));
}

int main(int argc,char **argv) {
    (void)argc;(void)argv;
    DkDevice device=NULL;
    DkQueue queue=NULL;
    DkCmdBuf cmd=NULL;
    DkSwapchain swapchain=NULL;
    DkMemBlock images_mem[BUFFER_COUNT]={0};
    DkMemBlock cmd_mem=NULL;
    DkImage images[BUFFER_COUNT];
    DkImageView views[BUFFER_COUNT];
    DkImageLayout layout;

    DkDeviceMaker device_maker;
    dkDeviceMakerDefaults(&device_maker);
    /* These are the deko3d defaults and match GPU vertex staging:
     * clip-space Z 0..1, upper-left image origin, +Y upward. */
    device_maker.flags=DkDeviceFlags_DepthZeroToOne |
                       DkDeviceFlags_OriginUpperLeft |
                       DkDeviceFlags_YAxisPointsUp;
    device=dkDeviceCreate(&device_maker);
    if (!device) return 2;

    DkQueueMaker queue_maker;
    dkQueueMakerDefaults(&queue_maker,device);
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
    const uint32_t image_bytes=round_up(dkImageLayoutGetSize(&layout),
                                           DK_MEMBLOCK_ALIGNMENT);
    if (!image_bytes) goto cleanup;

    for (unsigned i=0;i<BUFFER_COUNT;++i) {
        DkMemBlockMaker image_maker;
        dkMemBlockMakerDefaults(&image_maker,device,image_bytes);
        image_maker.flags=DkMemBlockFlags_CpuUncached |
                          DkMemBlockFlags_GpuCached |
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

    padConfigureInput(1,HidNpadStyleSet_NpadStandard);
    PadState pad;
    padInitializeDefault(&pad);
    unsigned frame=0;
    while (appletMainLoop()) {
        padUpdate(&pad);
        if (padGetButtonsDown(&pad)&HidNpadButton_Plus) break;

        const int slot=dkQueueAcquireImage(queue,swapchain);
        if (slot<0 || slot>=BUFFER_COUNT)break;

        /* Synchronize after each frame intentionally. This is a
         * correctness smoke test, NOT a performance benchmark. */
        dkCmdBufClear(cmd);
        DkImageView const* color_targets[] = { &views[slot] };
        dkCmdBufBindRenderTargets(cmd,color_targets,1,NULL);
        float phase=(float)(frame%240)/239.0f;
        dkCmdBufClearColorFloat(cmd,0,DkColorMask_RGBA,
                                .09f+.15f*phase,.12f+.35f*phase,
                                .23f+.30f*phase,1.0f);
        DkCmdList commands=dkCmdBufFinishList(cmd);
        dkQueueSubmitCommands(queue,commands);
        dkQueueFlush(queue);
        dkQueueWaitIdle(queue);
        dkQueuePresentImage(queue,swapchain,slot);
        ++frame;
    }
cleanup:
    if (queue)dkQueueWaitIdle(queue);
    if (cmd)dkCmdBufDestroy(cmd);
    if (cmd_mem)dkMemBlockDestroy(cmd_mem);
    if (swapchain)dkSwapchainDestroy(swapchain);
    for (unsigned i=0;i<BUFFER_COUNT;++i)
        if (images_mem[i])dkMemBlockDestroy(images_mem[i]);
    if (queue)dkQueueDestroy(queue);
    dkDeviceDestroy(device);
    return 0;
}
