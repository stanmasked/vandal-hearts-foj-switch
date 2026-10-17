/* Stage 168: generated-only private SD boot breadcrumbs, no Switch GPU.
 * Tests that relaunch never overwrites older evidence or private files. */
#define _POSIX_C_SOURCE 200809L
#ifdef NDEBUG
#undef NDEBUG
#endif
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <unistd.h>
#include "gpu_boot_journal.h"

static void path_for(char *dst,size_t cap,const char *prefix,unsigned slot) {
    assert(snprintf(dst,cap,"%s%02u.txt",prefix,slot)>0);
}
static void test_record_and_recovery(void) {
    char dir[]="/tmp/foj-boot-stage168-XXXXXX";
    assert(mkdtemp(dir));
    char prefix[256];
    assert(snprintf(prefix,sizeof(prefix),"%s/foj-boot-",dir)>0);
    FojGpuBootJournal journal={0};
    assert(foj_gpu_boot_journal_begin(&journal,prefix));
    assert(journal.slot==0);
    assert(foj_gpu_boot_journal_note(&journal,FOJ_BOOT_DEVICE,FOJ_BOOT_ENTER,0));
    assert(foj_gpu_boot_journal_note(&journal,FOJ_BOOT_DEVICE,FOJ_BOOT_FAILED,0));
    assert(foj_gpu_boot_journal_note(&journal,FOJ_BOOT_EXIT,FOJ_BOOT_EXITED,0));
    assert(journal.records==3);
    foj_gpu_boot_journal_close(&journal);
    char filename[300];
    path_for(filename,sizeof(filename),prefix,0);
    FILE *input=fopen(filename,"rb");
    assert(input);
    char line[120];
    assert(fgets(line,sizeof(line),input));
    assert(!strcmp(line,"FOJBOOT1 slot=00 step=01 event=1 frames=0000000000\n"));
    assert(fgets(line,sizeof(line),input));
    assert(!strcmp(line,"FOJBOOT1 slot=00 step=01 event=3 frames=0000000000\n"));
    assert(fgets(line,sizeof(line),input));
    assert(!strcmp(line,"FOJBOOT1 slot=00 step=11 event=4 frames=0000000000\n"));
    assert(!fgets(line,sizeof(line),input));
    assert(fclose(input)==0);
    /* Relaunch creates slot 01 without modifying slot 00. */
    assert(foj_gpu_boot_journal_begin(&journal,prefix));
    assert(journal.slot==1);
    assert(foj_gpu_boot_journal_note(&journal,FOJ_BOOT_DEVICE,FOJ_BOOT_READY,0));
    assert(foj_gpu_boot_journal_note(&journal,FOJ_BOOT_QUEUE,FOJ_BOOT_FAILED,0));
    foj_gpu_boot_journal_close(&journal);
    /* Existing symlink in slot 02 must not be followed or truncated. */
    char symlink_name[300];
    path_for(symlink_name,sizeof(symlink_name),prefix,2);
    assert(symlink(filename,symlink_name)==0);
    assert(foj_gpu_boot_journal_begin(&journal,prefix));
    assert(journal.slot==3);
    assert(foj_gpu_boot_journal_note(&journal,FOJ_BOOT_PRESENT,FOJ_BOOT_ENTER,0));
    assert(foj_gpu_boot_journal_note(&journal,FOJ_BOOT_PRESENT,FOJ_BOOT_READY,5));
    assert(foj_gpu_boot_journal_note(&journal,FOJ_BOOT_EXIT,FOJ_BOOT_EXITED,5));
    foj_gpu_boot_journal_close(&journal);
    input=fopen(filename,"rb");
    assert(input);
    assert(fgets(line,sizeof(line),input));
    assert(!strcmp(line,"FOJBOOT1 slot=00 step=01 event=1 frames=0000000000\n"));
    assert(fclose(input)==0);
    assert(unlink(symlink_name)==0);
    for(unsigned i=0;i<FOJ_GPU_BOOT_JOURNAL_SLOTS;++i) {
        path_for(filename,sizeof(filename),prefix,i);
        /* Fill available slots without clobbering earlier contents. */
        if(i>=4) {
            assert(foj_gpu_boot_journal_begin(&journal,prefix));
            assert(journal.slot==i);
            foj_gpu_boot_journal_close(&journal);
        }
    }
    assert(!foj_gpu_boot_journal_begin(&journal,prefix));
    assert(journal.file==NULL);
    for(unsigned i=0;i<FOJ_GPU_BOOT_JOURNAL_SLOTS;++i) {
        path_for(filename,sizeof(filename),prefix,i);
        assert(unlink(filename)==0);
    }
    assert(rmdir(dir)==0);
}
static void test_bounds_and_disabled(void) {
    FojGpuBootJournal journal={0};
    assert(!foj_gpu_boot_journal_begin(NULL,"/tmp/invalid-"));
    assert(!foj_gpu_boot_journal_begin(&journal,NULL));
    assert(!foj_gpu_boot_journal_begin(&journal,""));
    char excessive[260];
    memset(excessive,'x',sizeof(excessive)-1);
    excessive[sizeof(excessive)-1]=0;
    assert(!foj_gpu_boot_journal_begin(&journal,excessive));
    assert(!foj_gpu_boot_journal_begin(&journal,
                                       "/tmp/foj-stage168-does-not-exist-/file"));
    assert(!foj_gpu_boot_journal_note(&journal,FOJ_BOOT_DEVICE,FOJ_BOOT_ENTER,0));
    char dir[]="/tmp/foj-boot-stage168-cap-XXXXXX";
    assert(mkdtemp(dir));
    char prefix[256],filename[300];
    assert(snprintf(prefix,sizeof(prefix),"%s/attempt-",dir)>0);
    assert(foj_gpu_boot_journal_begin(&journal,prefix));
    assert(!foj_gpu_boot_journal_note(&journal,(FojGpuBootStage)0,FOJ_BOOT_ENTER,0));
    assert(!foj_gpu_boot_journal_note(&journal,FOJ_BOOT_DEVICE,(FojGpuBootEvent)0,0));
    assert(!foj_gpu_boot_journal_note(&journal,(FojGpuBootStage)12,FOJ_BOOT_ENTER,0));
    for(unsigned n=0;n<64;++n)
        assert(foj_gpu_boot_journal_note(
            &journal,FOJ_BOOT_PRESENT,FOJ_BOOT_READY,(uint32_t)n));
    assert(journal.records==64);
    assert(!foj_gpu_boot_journal_note(
        &journal,FOJ_BOOT_EXIT,FOJ_BOOT_EXITED,UINT32_MAX));
    foj_gpu_boot_journal_close(&journal);
    foj_gpu_boot_journal_close(&journal);
    path_for(filename,sizeof(filename),prefix,0);
    FILE *input=fopen(filename,"rb");
    assert(input);
    unsigned rows=0;
    char line[120];
    while(fgets(line,sizeof(line),input)) {
        assert(strncmp(line,"FOJBOOT1 slot=00",16)==0);
        assert(strstr(line,"/tmp/")==NULL);
        rows++;
    }
    assert(rows==64);
    assert(fclose(input)==0);
    assert(unlink(filename)==0);
    assert(rmdir(dir)==0);
}
int main(void) {
    test_record_and_recovery();
    test_bounds_and_disabled();
    puts("Stage 168 exclusive-new SD boot journal and relaunch: PASS");
    return 0;
}
