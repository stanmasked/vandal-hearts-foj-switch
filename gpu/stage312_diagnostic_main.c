/*
 * Stage312-only runtime breadcrumbs for isolating a missing first GPU frame.
 * The wrapped calls are still the real libnx/deko3d functions. Diagnostics
 * are fixed-code, bounded, best-effort, and never affect the return values.
 */
#include <switch.h>
#include <deko3d.h>
#include <stdio.h>
#include "dds_screen_status.h"

/* Stage312 alone samples generated DDS statuses for four frames per slot,
 * then reaches its actual texture GPU scene after 12 frames, not 360.
 * The shared 120-frame policy stays unchanged for all other NROs.
 * Include the enum declaration before the macro to avoid rewriting it.
 */
_Static_assert(FOJ_GPU_DDS_STATUS_FRAMES_PER_SLOT==120,
               "Stage312 status-frame baseline changed");
#define FOJ_GPU_DDS_STATUS_FRAMES_PER_SLOT 4u

#if !defined(FOJ_GPU_STAGE312_HORIZONTAL_GUTTER)
#error "Stage312 diagnostic wrapper must only be built for the horizontal gutter NRO"
#endif

enum { STAGE312_PROGRESS_MAX_RECORDS=24 };
static FILE *stage312_progress_file;
static unsigned stage312_progress_records;
static int stage312_progress_disabled;

static void stage312_progress(unsigned phase) {
    if (stage312_progress_disabled ||
        stage312_progress_records>=STAGE312_PROGRESS_MAX_RECORDS)
        return;
    if (!stage312_progress_file) {
        stage312_progress_file=fopen(
            "sdmc:/switch/foj/gpu/foj-stage312-frame-progress.txt","wx");
        if (!stage312_progress_file) {
            stage312_progress_disabled=1;
            return;
        }
    }
    if (fprintf(stage312_progress_file,"FOJ312P1 phase=%u\n",phase)<0 ||
        fflush(stage312_progress_file)!=0) {
        fclose(stage312_progress_file);
        stage312_progress_file=NULL;
        stage312_progress_disabled=1;
        return;
    }
    ++stage312_progress_records;
}

/* Sparse numeric milestones only: no paths, pixels or guest log data. */
static void stage312_presented_checkpoint(unsigned frames) {
    if (frames!=1u && frames!=2u && frames!=4u && frames!=8u &&
        frames!=12u && frames!=13u && frames!=16u && frames!=32u &&
        frames!=64u && frames!=128u && frames!=256u &&
        frames!=360u && frames!=512u && frames!=1024u)
        return;
    if (stage312_progress_disabled || !stage312_progress_file ||
        stage312_progress_records>=STAGE312_PROGRESS_MAX_RECORDS)
        return;
    if (fprintf(stage312_progress_file,"FOJ312F1 frames=%010u\n",
                frames)<0 || fflush(stage312_progress_file)!=0) {
        fclose(stage312_progress_file);
        stage312_progress_file=NULL;
        stage312_progress_disabled=1;
        return;
    }
    ++stage312_progress_records;
}

static void stage312_diag_pad_update(PadState *state) {
    static unsigned calls;
    if (calls==0u)stage312_progress(0u);
    padUpdate(state);
    if (calls==0u)stage312_progress(1u);
    ++calls;
}

static int stage312_diag_acquire(DkQueue queue,DkSwapchain swapchain) {
    static unsigned calls;
    if (calls==0u)stage312_progress(2u);
    const int slot=dkQueueAcquireImage(queue,swapchain);
    if (calls==0u)stage312_progress(3u);
    ++calls;
    return slot;
}

static void stage312_diag_submit(DkQueue queue,DkCmdList commands) {
    static unsigned calls;
    /* Submit #0 is the generated texture upload; #1 is the first frame. */
    const unsigned call=calls++;
    if (call==1u)stage312_progress(4u);
    dkQueueSubmitCommands(queue,commands);
    if (call==1u)stage312_progress(5u);
}

static void stage312_diag_present(DkQueue queue,DkSwapchain swapchain,
                                  int image_slot) {
    static unsigned calls;
    if (calls==0u)stage312_progress(6u);
    dkQueuePresentImage(queue,swapchain,image_slot);
    if (calls==0u)stage312_progress(7u);
    const unsigned presented=++calls;
    stage312_presented_checkpoint(presented);
}

#define padUpdate(state) stage312_diag_pad_update((state))
#define dkQueueAcquireImage(queue,swapchain) \
    stage312_diag_acquire((queue),(swapchain))
#define dkQueueSubmitCommands(queue,commands) \
    stage312_diag_submit((queue),(commands))
#define dkQueuePresentImage(queue,swapchain,image_slot) \
    stage312_diag_present((queue),(swapchain),(image_slot))

#include "deko3d_clear_main.c"
