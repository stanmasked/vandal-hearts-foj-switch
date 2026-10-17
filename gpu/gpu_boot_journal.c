#include "gpu_boot_journal.h"
#include <errno.h>
#include <stdio.h>
#include <string.h>
#include <limits.h>

enum { MAX_RECORDS=64, MAX_PREFIX=180 };
static int valid_stage(FojGpuBootStage stage) {
    return stage>=FOJ_BOOT_DEVICE && stage<=FOJ_BOOT_EXIT;
}
static int valid_event(FojGpuBootEvent event) {
    return event>=FOJ_BOOT_ENTER && event<=FOJ_BOOT_EXITED;
}
int foj_gpu_boot_journal_begin(FojGpuBootJournal *journal,
                                const char *trusted_prefix) {
    if (!journal)return 0;
    *journal=(FojGpuBootJournal){0};
    if (!trusted_prefix)return 0;
    const size_t n=strlen(trusted_prefix);
    if (n==0 || n>MAX_PREFIX)return 0;
    for (unsigned slot=0;slot<FOJ_GPU_BOOT_JOURNAL_SLOTS;++slot) {
        char path[MAX_PREFIX+16];
        const int len=snprintf(path,sizeof(path),"%s%02u.txt",
                               trusted_prefix,slot);
        if (len<0 || (size_t)len>=sizeof(path))return 0;
        /* C11 exclusive create: existing user files, including symlinks,
         * are NEVER followed or overwritten. */
        errno=0;
        FILE *fp=fopen(path,"wx");
        if (!fp) {
            if (errno==EEXIST)continue;
            return 0;
        }
        journal->file=fp;
        journal->slot=slot;
        return 1;
    }
    return 0; /* Full: never silently erase an earlier attempt. */
}
int foj_gpu_boot_journal_note(FojGpuBootJournal *journal,
                               FojGpuBootStage stage,FojGpuBootEvent event,
                               uint32_t frames) {
    if (!journal || !journal->file || !valid_stage(stage) ||
        !valid_event(event) || journal->records>=MAX_RECORDS)return 0;
    char line[72];
    const int n=snprintf(line,sizeof(line),
        "FOJBOOT1 slot=%02u step=%02u event=%u frames=%010u\n",
        journal->slot,(unsigned)stage,(unsigned)event,frames);
    if (n<=0 || (size_t)n>=sizeof(line))return 0;
    if (fwrite(line,1,(size_t)n,journal->file)!=(size_t)n ||
        fflush(journal->file)!=0) {
        /* No partial success claim: if SD is unwritable, disable logging
         * but never change the GPU startup/exit behavior. */
        foj_gpu_boot_journal_close(journal);
        return 0;
    }
    journal->records++;
    return 1;
}
void foj_gpu_boot_journal_close(FojGpuBootJournal *journal) {
    if (!journal)return;
    if (journal->file) {
        fclose(journal->file);
        journal->file=NULL;
    }
}
