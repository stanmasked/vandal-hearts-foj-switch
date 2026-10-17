#ifndef FOJ_GPU_BOOT_JOURNAL_H
#define FOJ_GPU_BOOT_JOURNAL_H
/* Optional fixed-code breadcrumbs on the user's own Switch SD card.
 * NO user paths, addresses, console identifiers, timestamps, PS3 assets,
 * shaders, pixel values, environment variables, or source hashes.
 * Up to 16 exclusive-new files; NEVER overwrite existing logs. */
#include <stdint.h>
#include <stdio.h>
enum { FOJ_GPU_BOOT_JOURNAL_SLOTS=16 };
typedef enum {
    FOJ_BOOT_DEVICE=1, FOJ_BOOT_QUEUE=2, FOJ_BOOT_IMAGES=3,
    FOJ_BOOT_SWAPCHAIN=4, FOJ_BOOT_COMMAND_BUFFER=5,
    FOJ_BOOT_VERTICES=6, FOJ_BOOT_SHADERS=7, FOJ_BOOT_TEXTURES=8,
    FOJ_BOOT_COMMAND_LISTS=9, FOJ_BOOT_PRESENT=10,
    FOJ_BOOT_EXIT=11
} FojGpuBootStage;
typedef enum { FOJ_BOOT_ENTER=1, FOJ_BOOT_READY=2,
               FOJ_BOOT_FAILED=3, FOJ_BOOT_EXITED=4 } FojGpuBootEvent;
typedef struct {
    FILE *file;
    unsigned slot;
    unsigned records;
} FojGpuBootJournal;
/* prefix must be a trusted constant: e.g. sdmc:/switch/foj/gpu/boot-
 * This opens prefix00.txt...prefix15.txt exclusively, never follows a
 * preexisting final-component symlink or truncates prior observations.
 * Failures are nonfatal to GPU boot and leave the journal disabled. */
int foj_gpu_boot_journal_begin(FojGpuBootJournal *journal,
                                const char *trusted_prefix);
/* Fixed ASCII line, no freeform fields. False means log unavailable.
 * Appends only, bounded to 64 records (no uncontrolled SD writes). */
int foj_gpu_boot_journal_note(FojGpuBootJournal *journal,
                               FojGpuBootStage stage,FojGpuBootEvent event,
                               uint32_t frames);
void foj_gpu_boot_journal_close(FojGpuBootJournal *journal);
#endif
