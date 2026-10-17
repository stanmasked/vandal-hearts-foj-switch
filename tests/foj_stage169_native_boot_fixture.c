/* Synthetic native C->Python boot journal conformance fixture.
 * Writes exclusively into a NEW private test directory supplied by caller.
 * No game assets, real Switch, GPU operations, paths in standard output.
 */
#include "gpu_boot_journal.h"
#include <stdio.h>

static int record(FojGpuBootJournal *j,FojGpuBootStage stage,
                  FojGpuBootEvent event,unsigned frames) {
    return foj_gpu_boot_journal_note(j,stage,event,frames);
}

int main(int argc,char **argv) {
    if (argc!=2)return 2;
    char prefix[256];
    const int n=snprintf(prefix,sizeof(prefix),"%s/foj-boot-",argv[1]);
    if (n<=0||(size_t)n>=sizeof(prefix))return 2;
    FojGpuBootJournal j={0};

    /* First synthetic launch: GPU queue creation failed before any frame. */
    if (!foj_gpu_boot_journal_begin(&j,prefix)||j.slot!=0)return 3;
    if (!record(&j,FOJ_BOOT_DEVICE,FOJ_BOOT_ENTER,0) ||
        !record(&j,FOJ_BOOT_DEVICE,FOJ_BOOT_READY,0) ||
        !record(&j,FOJ_BOOT_QUEUE,FOJ_BOOT_ENTER,0) ||
        !record(&j,FOJ_BOOT_QUEUE,FOJ_BOOT_FAILED,0) ||
        !record(&j,FOJ_BOOT_EXIT,FOJ_BOOT_EXITED,0))return 4;
    foj_gpu_boot_journal_close(&j);

    /* Second: every CPU initialization stage completed, CPU queued five
     * present calls, then an orderly, non-error exit. This is NOT a real
     * image being presented by a Nintendo Switch. */
    if (!foj_gpu_boot_journal_begin(&j,prefix)||j.slot!=1)return 5;
    for (int stage=FOJ_BOOT_DEVICE;stage<=FOJ_BOOT_PRESENT;++stage) {
        if (!record(&j,(FojGpuBootStage)stage,FOJ_BOOT_ENTER,0) ||
            !record(&j,(FojGpuBootStage)stage,FOJ_BOOT_READY,
                    stage==FOJ_BOOT_PRESENT?5u:0u))
            return 6;
    }
    if (!record(&j,FOJ_BOOT_EXIT,FOJ_BOOT_EXITED,5))return 7;
    foj_gpu_boot_journal_close(&j);
    puts("Stage 169 generated native CPU journal fixture: PASS");
    return 0;
}
