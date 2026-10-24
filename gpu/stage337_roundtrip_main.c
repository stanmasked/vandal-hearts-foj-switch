/* Stage337: generated-only deko3d GPU image copy roundtrip.
 * This research NRO uses no original PS3 assets, shaders or material paths.
 * A pass receipt is emitted only after two real GPU copy submissions,
 * queue synchronization, and an independent byte-for-byte RGBA comparison.
 */
#include <switch.h>
#include <deko3d.h>
#include <stdint.h>
#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "stage336_native_upload.h"

enum { W = 74, H = 81, PIXEL_BYTES = W * H * 4, CMD_BYTES = 0x10000 };

static uint8_t source_rgba[PIXEL_BYTES];
static void generate(void) {
    for (unsigned y = 0; y < H; ++y)
        for (unsigned x = 0; x < W; ++x) {
            const size_t n = 4u * ((size_t)y * W + x);
            source_rgba[n] = (uint8_t)(x * 3u + y * 5u + 17u);
            source_rgba[n+1u] = (uint8_t)(x * 11u + y * 7u + 23u);
            source_rgba[n+2u] = (uint8_t)(x * 13u + y * 2u + 91u);
            source_rgba[n+3u] = (uint8_t)((x * 9u + y * 3u) & 255u);
        }
}

static DkMemBlock command_memory(DkDevice device) {
    DkMemBlockMaker maker;
    dkMemBlockMakerDefaults(&maker, device, CMD_BYTES);
    maker.flags = DkMemBlockFlags_CpuUncached | DkMemBlockFlags_GpuCached;
    return dkMemBlockCreate(&maker);
}

static DkCmdBuf new_command_buffer(DkDevice device, DkMemBlock memory) {
    DkCmdBufMaker maker;
    dkCmdBufMakerDefaults(&maker, device);
    DkCmdBuf cmd = dkCmdBufCreate(&maker);
    if (cmd) dkCmdBufAddMemory(cmd, memory, 0, CMD_BYTES);
    return cmd;
}

static int verify_pixels(const uint8_t *readback, uint32_t row_pixels) {
    if (!readback || row_pixels < W || row_pixels > 2048u) return 0;
    for (unsigned y = 0; y < H; ++y) {
        const uint8_t *row = readback + 4u * (size_t)y * row_pixels;
        const uint8_t *expected = source_rgba + 4u * (size_t)y * W;
        if (memcmp(row, expected, W * 4u) != 0) return 0;
    }
    return 1;
}

static int run_native(void) {
    int rc = 1;
    DkDevice device = NULL;
    DkQueue queue = NULL;
    DkMemBlock cmds_mem = NULL, read_cmds_mem = NULL, read_mem = NULL;
    DkCmdBuf cmd = NULL, read_cmd = NULL;
    FojStage336NativeTexture uploaded = {0};
    generate();

    DkDeviceMaker devmaker;
    dkDeviceMakerDefaults(&devmaker);
    devmaker.flags = DkDeviceFlags_DepthZeroToOne | DkDeviceFlags_OriginUpperLeft;
    device = dkDeviceCreate(&devmaker);
    if (!device) goto cleanup;
    DkQueueMaker qmaker;
    dkQueueMakerDefaults(&qmaker, device);
    qmaker.flags = DkQueueFlags_Graphics;
    queue = dkQueueCreate(&qmaker);
    if (!queue) goto cleanup;
    cmds_mem = command_memory(device);
    read_cmds_mem = command_memory(device);
    if (!cmds_mem || !read_cmds_mem) goto cleanup;
    cmd = new_command_buffer(device, cmds_mem);
    read_cmd = new_command_buffer(device, read_cmds_mem);
    if (!cmd || !read_cmd) goto cleanup;

    const FojStage332DdsInfo info = { W, H, 1u, FOJ_STAGE332_BGRA8, PIXEL_BYTES };
    if (!foj_stage336_native_record_rgba_upload(device, cmd, &info,
            source_rgba, sizeof(source_rgba), 64u, &uploaded)) goto cleanup;
    const DkCmdList submit = dkCmdBufFinishList(cmd);
    if (!submit) goto cleanup;
    dkQueueSubmitCommands(queue, submit);
    dkQueueWaitIdle(queue);
    if (dkQueueIsInErrorState(queue)) goto cleanup;

    DkMemBlockMaker rm;
    dkMemBlockMakerDefaults(&rm, device, uploaded.plan.staging_allocation_bytes);
    rm.flags = DkMemBlockFlags_CpuUncached | DkMemBlockFlags_GpuCached;
    read_mem = dkMemBlockCreate(&rm);
    if (!read_mem) goto cleanup;
    uint8_t *read_cpu = (uint8_t*)dkMemBlockGetCpuAddr(read_mem);
    const DkGpuAddr read_gpu = dkMemBlockGetGpuAddr(read_mem);
    if (!read_cpu || read_gpu == DK_GPU_ADDR_INVALID) goto cleanup;
    memset(read_cpu, 0xa5, uploaded.plan.staging_allocation_bytes);
    const DkCopyBuf dst = {read_gpu, uploaded.plan.rows.row_length_pixels, H};
    const DkImageRect rect = {0, 0, 0, W, H, 1};
    dkCmdBufCopyImageToBuffer(read_cmd, &uploaded.image_view, &rect, &dst, 0);
    /* Delimit the readback and request a full copy-engine/cache barrier. */
    dkCmdBufBarrier(read_cmd, DkBarrier_Full, DkInvalidateFlags_L2Cache);
    const DkCmdList read_submit = dkCmdBufFinishList(read_cmd);
    if (!read_submit) goto cleanup;
    dkQueueSubmitCommands(queue, read_submit);
    dkQueueWaitIdle(queue);
    if (dkQueueIsInErrorState(queue)) goto cleanup;
    if (!verify_pixels(read_cpu, uploaded.plan.rows.row_length_pixels)) goto cleanup;
    rc = 0;
cleanup:
    if (queue && !dkQueueIsInErrorState(queue)) dkQueueWaitIdle(queue);
    if (read_mem) dkMemBlockDestroy(read_mem);
    foj_stage336_native_release(&uploaded);
    if (read_cmd) dkCmdBufDestroy(read_cmd);
    if (cmd) dkCmdBufDestroy(cmd);
    if (read_cmds_mem) dkMemBlockDestroy(read_cmds_mem);
    if (cmds_mem) dkMemBlockDestroy(cmds_mem);
    if (queue) dkQueueDestroy(queue);
    if (device) dkDeviceDestroy(device);
    return rc;
}

int main(void) {
    (void)fsdevMountSdmc();
    const int success = run_native() == 0;
    const char *const path =
        "sdmc:/switch/foj/gpu/foj-stage337-native-roundtrip.txt";
    if (success) {
        /* No previously stored or user-generated evidence may be reused. */
        FILE *const f = fopen(path, "wx");
        if (!f) return 11;
        static const char data[] =
            "STAGE337_DEKO3D_GPU_ROUNDTRIP_V1 w=74 h=81 pixels=5994 diff=0\n";
        const size_t n = fwrite(data, 1, sizeof(data) - 1u, f);
        const int flushed = fflush(f), closed = fclose(f);
        if (n != sizeof(data) - 1u || flushed || closed) return 12;
    }
    return success ? 0 : 10;
}
