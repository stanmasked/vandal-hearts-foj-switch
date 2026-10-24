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

enum { W = 74, H = 81, PIXEL_BYTES = W * H * 4,
       CMD_BYTES = 0x10000, GPU_ROW_ALIGNMENT = 256 };

static uint8_t source_rgba[PIXEL_BYTES];
/* Diagnostic progress is numeric and bounded; never includes guest logs,
 * GPU memory, filenames from user content or actual pixel data. It is NOT
 * a pass condition, merely failure localisation for headless emulation. */
static FILE *progress_file;
static unsigned progress_count;
static void progress(unsigned stage) {
    if (!progress_file || progress_count >= 24u || stage > 99u) return;
    if (fprintf(progress_file, "FOJ337P1 stage=%02u\n", stage) < 0 ||
        fflush(progress_file) != 0) {
        fclose(progress_file);
        progress_file = NULL;
        return;
    }
    ++progress_count;
}
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
    progress(1u);

    DkDeviceMaker devmaker;
    dkDeviceMakerDefaults(&devmaker);
    devmaker.flags = DkDeviceFlags_DepthZeroToOne | DkDeviceFlags_OriginUpperLeft;
    device = dkDeviceCreate(&devmaker);
    if (!device) goto cleanup;
    progress(2u);
    DkQueueMaker qmaker;
    dkQueueMakerDefaults(&qmaker, device);
    qmaker.flags = DkQueueFlags_Graphics;
    queue = dkQueueCreate(&qmaker);
    if (!queue) goto cleanup;
    progress(3u);
    cmds_mem = command_memory(device);
    read_cmds_mem = command_memory(device);
    if (!cmds_mem || !read_cmds_mem) goto cleanup;
    cmd = new_command_buffer(device, cmds_mem);
    read_cmd = new_command_buffer(device, read_cmds_mem);
    if (!cmd || !read_cmd) goto cleanup;
    progress(4u);

    const FojStage332DdsInfo info = { W, H, 1u, FOJ_STAGE332_BGRA8, PIXEL_BYTES };
    if (!foj_stage336_native_record_rgba_upload(device, cmd, &info,
            source_rgba, sizeof(source_rgba), GPU_ROW_ALIGNMENT, &uploaded)) goto cleanup;
    progress(5u);
    const DkCmdList submit = dkCmdBufFinishList(cmd);
    if (!submit) goto cleanup;
    dkQueueSubmitCommands(queue, submit);
    progress(6u);
    dkQueueWaitIdle(queue);
    progress(7u);
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
    progress(8u);
    const DkCopyBuf dst = {read_gpu, uploaded.plan.rows.row_length_pixels, H};
    const DkImageRect rect = {0, 0, 0, W, H, 1};
    dkCmdBufCopyImageToBuffer(read_cmd, &uploaded.image_view, &rect, &dst, 0);
    progress(9u);
    /* Delimit the readback and request a full copy-engine/cache barrier. */
    dkCmdBufBarrier(read_cmd, DkBarrier_Full, DkInvalidateFlags_L2Cache);
    const DkCmdList read_submit = dkCmdBufFinishList(read_cmd);
    if (!read_submit) goto cleanup;
    dkQueueSubmitCommands(queue, read_submit);
    progress(10u);
    dkQueueWaitIdle(queue);
    progress(11u);
    if (dkQueueIsInErrorState(queue)) {
        progress(80u); /* GPU queue error after readback. */
        goto cleanup;
    }
    /*
     * Readback block is CPU-uncached but GPU-cached. dkQueueWaitIdle waits
     * for the submitted operations, whereas a flushed GPU fence explicitly
     * makes GPU-cache writes visible to other agents such as the CPU.
     * This is an opt-in diagnostic experiment, NOT presumed proof of
     * correct pixels or physical Switch behaviour.
     */
    DkFence visibility_fence = {0};
    dkQueueSignalFence(queue, &visibility_fence, true);
    dkQueueWaitFence(queue, &visibility_fence);
    if (dkQueueIsInErrorState(queue)) {
        progress(85u); /* Fault while flushing GPU-side write visibility. */
        goto cleanup;
    }
    progress(12u); /* Queue healthy and GPU-cache flushed; compare RGBA. */
    if (!verify_pixels(read_cpu, uploaded.plan.rows.row_length_pixels)) {
        /*
         * Synthetic-only failure classification. These numbers are NOT
         * evidence of successful GPU work and expose no source/game bytes.
         * All reads are within the validated row-padded allocation.
         */
        size_t rgb_bad = 0u, alpha_bad = 0u, unchanged = 0u;
        for (unsigned y=0; y<H; ++y) {
            const uint8_t *got = read_cpu +
                4u * (size_t)y * uploaded.plan.rows.row_length_pixels;
            const uint8_t *want = source_rgba + 4u * (size_t)y * W;
            for (unsigned k=0; k<W*4u; ++k) {
                if (got[k] == 0xa5u) ++unchanged;
                if (got[k] != want[k]) {
                    if (k%4u == 3u) ++alpha_bad;
                    else ++rgb_bad;
                }
            }
        }
        /*
         * Disambiguate the observed mixed-channel failure without printing
         * the synthesized pixels or copying any untrusted buffers. Every
         * read below stays within the checked padded readback allocation.
         */
        size_t all_zero = 0u, all_ff = 0u;
        int bgr_swap = 1, tight_rows = 1, upside_down = 1;
        for (unsigned y = 0u; y < H; ++y) {
            const uint8_t *row = read_cpu +
                (size_t)y * uploaded.plan.rows.row_length_pixels * 4u;
            const uint8_t *tight = read_cpu + (size_t)y * W * 4u;
            const uint8_t *forward = source_rgba + (size_t)y * W * 4u;
            const uint8_t *reverse = source_rgba + (size_t)(H-1u-y) * W * 4u;
            for (unsigned x = 0u; x < W; ++x) {
                const size_t k = (size_t)x * 4u;
                for (unsigned n = 0u; n < 4u; ++n) {
                    all_zero += row[k+n] == 0u;
                    all_ff += row[k+n] == 255u;
                }
                if (row[k] != forward[k+2u] ||
                    row[k+1u] != forward[k+1u] ||
                    row[k+2u] != forward[k] ||
                    row[k+3u] != forward[k+3u]) bgr_swap = 0;
                if (memcmp(tight+k,forward+k,4u)) tight_rows = 0;
                if (memcmp(row+k,reverse+k,4u)) upside_down = 0;
            }
        }
        if (unchanged == PIXEL_BYTES) progress(81u);
        else if (all_zero == PIXEL_BYTES) progress(86u); /* All zero. */
        else if (all_ff == PIXEL_BYTES) progress(87u); /* All 0xff. */
        else if (bgr_swap) progress(88u); /* RGBA/BGRA swap. */
        else if (tight_rows) progress(89u); /* Row pitch mismatch. */
        else if (upside_down) progress(90u); /* Reversed row order. */
        else {
            /*
             * Stage337.7: determine if a GPU driver used a different
             * uniform row pitch than the requested padded DkCopyBuf.
             * The declared layout uses 512 B per row for this 74x81
             * fixture. Examine only alternative candidate byte pitches
             * whose LAST row fits within the allocated readback buffer.
             */
            static const uint32_t other_pitches[] = {320u,384u,448u};
            unsigned alternate = 0u;
            for (unsigned p = 0u; p < 3u; ++p) {
                const size_t pitch = other_pitches[p];
                if (pitch < W*4u ||
                    (size_t)(H-1u)*pitch + W*4u >
                    uploaded.plan.staging_allocation_bytes) continue;
                int matches = 1;
                for (unsigned y = 0u; y < H; ++y) {
                    const uint8_t *row = read_cpu + (size_t)y * pitch;
                    const uint8_t *expect = source_rgba + (size_t)y*W*4u;
                    if (memcmp(row,expect,W*4u)) { matches=0; break; }
                }
                if (matches) { alternate = 92u + p; break; }
            }
            if (alternate) progress(alternate); /* alternate full pitch */
            else if (!memcmp(read_cpu,source_rgba,W*4u)) progress(91u);
            else if (!rgb_bad && alpha_bad) progress(82u);
            else if (rgb_bad && !alpha_bad) progress(83u);
            else progress(84u);
        }
        /*
         * Failure remains failure: numeric reports are not accepted as
         * a GPU success receipt, even when one alternate pitch matched.
         */
        goto cleanup;

    }
    progress(13u); /* Validated byte-for-byte copy. */
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
    progress_file = fopen("sdmc:/switch/foj/gpu/foj-stage337-progress.txt", "wx");
    progress(0u);
    const int success = run_native() == 0;
    /* Preserve the last completed milestone on failure. Only full success
     * advances to 13, after both GPU submissions and exact pixel comparison. */
    if (success) progress(13u);
    if (progress_file) {
        fclose(progress_file);
        progress_file = NULL;
    }
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
