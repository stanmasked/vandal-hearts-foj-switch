/*
 * Stage340: owner-local DDS -> real deko3d image -> GPU readback roundtrip.
 *
 * The NRO contains NO original game assets. It reads exactly one caller-supplied
 * 256x256 classic BGRA8 DDS from SD, preflights it via Stage339, uploads the
 * decoded RGBA8 via Stage336, copies the actual DkImage back to CPU memory,
 * and emits a fixed aggregate receipt only after byte-exact comparison.
 * Use synthetic DDS in public CI. Original DDS runs are owner-local only.
 */
#include <switch.h>
#include <deko3d.h>
#include <stdint.h>
#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "stage332_dds_source.h"
#include "stage339_private_dds_bridge.h"
#include "stage336_native_upload.h"

enum {
    W = 256, H = 256, RGBA_BYTES = W * H * 4,
    MAX_DDS_BYTES = 1024 * 1024,
    CMD_BYTES = 0x10000,
    GPU_ROW_ALIGNMENT = 256
};
#define SOURCE_PATH "sdmc:/switch/foj/gpu/source.dds"
#define PROGRESS_PATH "sdmc:/switch/foj/gpu/foj-stage340-progress.txt"
#define RECEIPT_PATH "sdmc:/switch/foj/gpu/foj-stage340-native-dds-roundtrip.txt"

static uint8_t source_dds[MAX_DDS_BYTES];
static uint8_t decoded_rgba[RGBA_BYTES];
static FILE *progress_file;
static unsigned progress_count;

static void progress(unsigned stage) {
    if (!progress_file || progress_count >= 24u || stage > 99u) return;
    if (fprintf(progress_file, "FOJ340P1 stage=%02u\n", stage) < 0 ||
        fflush(progress_file) != 0) {
        fclose(progress_file);
        progress_file = NULL;
        return;
    }
    ++progress_count;
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

static int read_source_dds(size_t *out_size, FojStage332DdsInfo *out_info) {
    FILE *f = NULL;
    size_t length;
    long measured;
    if (!out_size || !out_info) return 0;
    f = fopen(SOURCE_PATH, "rb");
    if (!f) return 0;
    if (fseek(f, 0, SEEK_END) != 0) goto fail;
    measured = ftell(f);
    if (measured < 128 || (uint64_t)measured > MAX_DDS_BYTES ||
        fseek(f, 0, SEEK_SET) != 0)
        goto fail;
    length = (size_t)measured;
    if (fread(source_dds, 1, length, f) != length ||
        fgetc(f) != EOF || ferror(f) || fseek(f, 0, SEEK_SET) != 0)
        goto fail;
    /* Re-read in bounded chunks to refuse an input changing during intake. */
    {
        uint8_t check[4096];
        size_t offset = 0;
        while (offset < length) {
            const size_t amount = length - offset < sizeof(check) ?
                                  length - offset : sizeof(check);
            if (fread(check, 1, amount, f) != amount ||
                memcmp(check, source_dds + offset, amount) != 0)
                goto fail;
            offset += amount;
        }
        if (fgetc(f) != EOF || ferror(f)) goto fail;
    }
    const int close_status = fclose(f);
    f = NULL;
    if (close_status != 0) return 0;
    FojStage332DdsInfo info;
    if (!foj_stage332_dds_inspect(source_dds, length, &info) ||
        info.width != W || info.height != H ||
        info.format != FOJ_STAGE332_BGRA8 ||
        info.mip_levels != 1u || info.rgba_bytes != RGBA_BYTES)
        return 0;
    *out_size = length;
    *out_info = info;
    return 1;
fail:
    if (f) fclose(f);
    return 0;
}

static int plan_equal(const FojStage336GpuCopyPlan *a,
                      const FojStage336GpuCopyPlan *b) {
    return a && b &&
        a->rows.width == b->rows.width &&
        a->rows.height == b->rows.height &&
        a->rows.row_length_pixels == b->rows.row_length_pixels &&
        a->rows.row_pitch_bytes == b->rows.row_pitch_bytes &&
        a->rows.rgba_bytes == b->rows.rgba_bytes &&
        a->rows.staging_bytes == b->rows.staging_bytes &&
        a->staging_allocation_bytes == b->staging_allocation_bytes &&
        a->image_allocation_bytes == b->image_allocation_bytes &&
        a->image_alignment_bytes == b->image_alignment_bytes;
}

static int verify_readback(const uint8_t *readback,
                           const FojStage336GpuCopyPlan *plan) {
    size_t differing_channels = 0u;
    if (!readback || !plan || plan->rows.width != W ||
        plan->rows.height != H ||
        plan->rows.row_pitch_bytes < W * 4u ||
        plan->rows.row_length_pixels != W ||
        plan->rows.rgba_bytes != RGBA_BYTES ||
        plan->staging_allocation_bytes < RGBA_BYTES)
        return 0;
    for (unsigned y = 0; y < H; ++y) {
        const uint8_t *got = readback +
            (size_t)y * plan->rows.row_pitch_bytes;
        const uint8_t *want = decoded_rgba + (size_t)y * W * 4u;
        for (size_t x = 0; x < W * 4u; ++x)
            differing_channels += got[x] != want[x];
    }
    return differing_channels == 0u;
}

static int run_native(void) {
    int rc = 1;
    size_t dds_size = 0;
    FojStage332DdsInfo info = {0};
    FojStage339Prepared prepared = {0};
    FojStage336NativeTexture uploaded = {0};
    DkDevice device = NULL;
    DkQueue queue = NULL;
    DkMemBlock upload_mem = NULL, read_mem = NULL, read_cmd_mem = NULL;
    DkCmdBuf upload_cmd = NULL, read_cmd = NULL;

    progress(1u);
    if (!read_source_dds(&dds_size, &info)) goto cleanup;
    progress(2u);

    DkDeviceMaker devmaker;
    dkDeviceMakerDefaults(&devmaker);
    devmaker.flags = DkDeviceFlags_DepthZeroToOne | DkDeviceFlags_OriginUpperLeft;
    device = dkDeviceCreate(&devmaker);
    if (!device) goto cleanup;
    progress(3u);

    DkImageLayoutMaker layout_maker;
    DkImageLayout layout;
    dkImageLayoutMakerDefaults(&layout_maker, device);
    layout_maker.type = DkImageType_2D;
    layout_maker.format = DkImageFormat_RGBA8_Unorm;
    layout_maker.dimensions[0] = info.width;
    layout_maker.dimensions[1] = info.height;
    layout_maker.dimensions[2] = 1u;
    layout_maker.mipLevels = 1u;
    dkImageLayoutInitialize(&layout, &layout_maker);
    const uint64_t layout_bytes = dkImageLayoutGetSize(&layout);
    const uint32_t layout_alignment = dkImageLayoutGetAlignment(&layout);
    if (!foj_stage339_prepare_private_dds(
            source_dds, dds_size, decoded_rgba, sizeof(decoded_rgba),
            GPU_ROW_ALIGNMENT, layout_bytes, layout_alignment, &prepared) ||
        prepared.image.width != W || prepared.image.height != H ||
        prepared.image.format != FOJ_STAGE332_BGRA8 ||
        prepared.image.rgba_bytes != RGBA_BYTES ||
        prepared.gpu.rows.row_pitch_bytes != W * 4u ||
        prepared.gpu.rows.row_length_pixels != W)
        goto cleanup;
    progress(4u);

    DkQueueMaker qmaker;
    dkQueueMakerDefaults(&qmaker, device);
    qmaker.flags = DkQueueFlags_Graphics;
    queue = dkQueueCreate(&qmaker);
    if (!queue) goto cleanup;
    upload_mem = command_memory(device);
    if (!upload_mem) goto cleanup;
    upload_cmd = new_command_buffer(device, upload_mem);
    if (!upload_cmd) goto cleanup;
    progress(5u);

    if (!foj_stage336_native_record_rgba_upload(
            device, upload_cmd, &prepared.image, decoded_rgba,
            sizeof(decoded_rgba), GPU_ROW_ALIGNMENT, &uploaded) ||
        !plan_equal(&prepared.gpu, &uploaded.plan))
        goto cleanup;
    progress(6u);
    const DkCmdList upload_list = dkCmdBufFinishList(upload_cmd);
    if (!upload_list) goto cleanup;
    dkQueueSubmitCommands(queue, upload_list);
    dkQueueWaitIdle(queue);
    if (dkQueueIsInErrorState(queue)) goto cleanup;
    progress(7u);

    DkMemBlockMaker read_maker;
    dkMemBlockMakerDefaults(&read_maker, device,
                            uploaded.plan.staging_allocation_bytes);
    read_maker.flags = DkMemBlockFlags_CpuUncached | DkMemBlockFlags_GpuCached;
    read_mem = dkMemBlockCreate(&read_maker);
    if (!read_mem) goto cleanup;
    uint8_t *read_cpu = (uint8_t *)dkMemBlockGetCpuAddr(read_mem);
    const DkGpuAddr read_gpu = dkMemBlockGetGpuAddr(read_mem);
    if (!read_cpu || read_gpu == DK_GPU_ADDR_INVALID) goto cleanup;
    memset(read_cpu, 0xa5, uploaded.plan.staging_allocation_bytes);
    read_cmd_mem = command_memory(device);
    if (!read_cmd_mem) goto cleanup;
    read_cmd = new_command_buffer(device, read_cmd_mem);
    if (!read_cmd) goto cleanup;
    progress(8u);

    const DkCopyBuf destination = {
        read_gpu, uploaded.plan.rows.row_pitch_bytes, 0u
    };
    const DkImageRect rect = {0u, 0u, 0u, W, H, 1u};
    dkCmdBufCopyImageToBuffer(read_cmd, &uploaded.image_view,
                              &rect, &destination, 0u);
    dkCmdBufBarrier(read_cmd, DkBarrier_Full, DkInvalidateFlags_L2Cache);
    const DkCmdList read_list = dkCmdBufFinishList(read_cmd);
    if (!read_list) goto cleanup;
    dkQueueSubmitCommands(queue, read_list);
    dkQueueWaitIdle(queue);
    if (dkQueueIsInErrorState(queue)) goto cleanup;
    DkFence visibility_fence = {0};
    dkQueueSignalFence(queue, &visibility_fence, true);
    dkQueueWaitFence(queue, &visibility_fence);
    if (dkQueueIsInErrorState(queue)) goto cleanup;
    progress(9u);

    if (!verify_readback(read_cpu, &uploaded.plan)) goto cleanup;
    progress(10u);
    rc = 0;
cleanup:
    if (queue && !dkQueueIsInErrorState(queue)) dkQueueWaitIdle(queue);
    if (uploaded.image_mem || uploaded.staging_mem)
        foj_stage336_native_release(&uploaded);
    if (read_cmd) dkCmdBufDestroy(read_cmd);
    if (upload_cmd) dkCmdBufDestroy(upload_cmd);
    if (read_mem) dkMemBlockDestroy(read_mem);
    if (read_cmd_mem) dkMemBlockDestroy(read_cmd_mem);
    if (upload_mem) dkMemBlockDestroy(upload_mem);
    /* read_cmd_mem is owned separately from the upload command pool. */
    if (queue) dkQueueDestroy(queue);
    if (device) dkDeviceDestroy(device);
    return rc;
}

int main(void) {
    (void)fsdevMountSdmc();
    progress_file = fopen(PROGRESS_PATH, "wx");
    if (!progress_file) return 20;
    progress(0u);
    const int success = run_native() == 0;
    if (success) progress(13u);
    if (progress_file) {
        fclose(progress_file);
        progress_file = NULL;
    }
    if (!success) return 10;
    FILE *const receipt = fopen(RECEIPT_PATH, "wx");
    if (!receipt) return 11;
    static const char marker[] =
        "STAGE340_DEKO3D_DDS_GPU_ROUNDTRIP_V1 width=256 height=256 "
        "pixels=65536 diff=0 channels=0\n";
    const size_t n = fwrite(marker, 1, sizeof(marker) - 1u, receipt);
    const int flushed = fflush(receipt), closed = fclose(receipt);
    if (n != sizeof(marker) - 1u || flushed || closed) return 12;
    return 0;
}
