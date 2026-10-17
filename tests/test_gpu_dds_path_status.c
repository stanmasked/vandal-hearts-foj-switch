/* Stage 163: native file-descriptor DDS diagnostics and path guardrails.
 * Entirely invented tiny classic DDS inputs; no commercial source data. */
#define _POSIX_C_SOURCE 200809L
#ifdef NDEBUG
#undef NDEBUG
#endif
#include <assert.h>
#include <stdio.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <unistd.h>
#include "atlas_dds.h"

static void put32(uint8_t *p,unsigned off,uint32_t n) {
    for(unsigned i=0;i<4;++i)p[off+i]=(uint8_t)(n>>(8u*i));
}
static void generated(uint8_t out[384]) {
    memset(out,0,384);
    memcpy(out,"DDS ",4);
    put32(out,4,124);put32(out,8,0x100f);
    put32(out,12,8);put32(out,16,8);put32(out,20,32);
    put32(out,28,1);put32(out,76,32);put32(out,80,0x41);
    put32(out,88,32);put32(out,92,0xff);
    put32(out,96,0x0000ff00);put32(out,100,0x00ff0000);
    put32(out,104,0xff000000);put32(out,108,0x1000);
    for(unsigned i=128;i<384;++i)out[i]=(uint8_t)(i*3u);
}
static void write_test_file(const char *name,const uint8_t *bytes,size_t count) {
    FILE *fp=fopen(name,"wb");
    assert(fp);
    assert(fwrite(bytes,1,count,fp)==count);
    assert(fclose(fp)==0);
}
static void expect_rejected(const char *name,FojAtlasDdsStatus expected) {
    uint8_t pixels[256];
    memset(pixels,0xa5,sizeof(pixels));
    FojAtlasRgba8Info atlas={7,8,9};
    FojAtlasDdsStatus status=FOJ_ATLAS_DDS_LOADED;
    const int result=foj_atlas_dds_try_read_status(
        name,pixels,sizeof(pixels),&atlas,&status);
    assert(result==-1);
    assert(status==expected);
    assert(atlas.width==7 && atlas.height==8 && atlas.pixel_bytes==9);
    for (size_t i=0;i<sizeof(pixels);++i)assert(pixels[i]==0xa5);
}
static void test_regular_missing_invalid_and_compat(void) {
    const char *valid="build/foj-stage163-ok.dds";
    const char *missing="build/foj-stage163-definitely-missing.dds";
    const char *invalid="build/foj-stage163-malformed.dds";
    uint8_t bytes[384];
    generated(bytes);
    write_test_file(valid,bytes,sizeof(bytes));
    const uint8_t bad[]={0x42,0x42,0x42,0x42};
    write_test_file(invalid,bad,sizeof(bad));
    uint8_t pixels[256];
    memset(pixels,0xa5,sizeof(pixels));
    FojAtlasRgba8Info atlas={0};
    FojAtlasDdsStatus status=FOJ_ATLAS_DDS_INVALID_ARGUMENT;
    assert(foj_atlas_dds_try_read_status(
        valid,pixels,sizeof(pixels),&atlas,&status)==1);
    assert(status==FOJ_ATLAS_DDS_LOADED);
    assert(atlas.width==8 && atlas.height==8 && atlas.pixel_bytes==256);
    assert(!memcmp(pixels,bytes+128,256));
    assert(foj_atlas_dds_try_read(valid,pixels,sizeof(pixels),&atlas)==1);
    memset(pixels,0xa5,sizeof(pixels));
    atlas=(FojAtlasRgba8Info){7,8,9};
    status=FOJ_ATLAS_DDS_LOADED;
    assert(foj_atlas_dds_try_read_status(
        missing,pixels,sizeof(pixels),&atlas,&status)==0);
    assert(status==FOJ_ATLAS_DDS_MISSING);
    assert(atlas.width==7 && atlas.height==8);
    for(size_t i=0;i<sizeof(pixels);++i)assert(pixels[i]==0xa5);
    expect_rejected(invalid,FOJ_ATLAS_DDS_INVALID_FORMAT);
    bytes[0]='X';
    write_test_file(valid,bytes,sizeof(bytes));
    expect_rejected(valid,FOJ_ATLAS_DDS_INVALID_FORMAT);
    assert(remove(valid)==0);
    assert(remove(invalid)==0);
}
static void test_symlinks_regular_directory_and_fifo(void) {
    const char *file="build/foj-stage163-regular.dds";
    const char *link="build/foj-stage163-link.dds";
    const char *broken="build/foj-stage163-broken.dds";
    const char *dir="build/foj-stage163-directory.dds";
    const char *fifo="build/foj-stage163-fifo.dds";
    uint8_t bytes[384];
    generated(bytes);
    write_test_file(file,bytes,sizeof(bytes));
    assert(symlink("foj-stage163-regular.dds",link)==0);
    expect_rejected(link,FOJ_ATLAS_DDS_PATH_REJECTED);
    assert(symlink("foj-stage163-absent-target.dds",broken)==0);
    expect_rejected(broken,FOJ_ATLAS_DDS_PATH_REJECTED);
    assert(mkdir(dir,0700)==0);
    expect_rejected(dir,FOJ_ATLAS_DDS_PATH_REJECTED);
    assert(mkfifo(fifo,0600)==0);
    expect_rejected(fifo,FOJ_ATLAS_DDS_PATH_REJECTED);
    assert(unlink(link)==0);
    assert(unlink(broken)==0);
    assert(unlink(fifo)==0);
    assert(rmdir(dir)==0);
    assert(remove(file)==0);
}
static void test_invalid_arguments_and_path_free_status_labels(void) {
    uint8_t buf[256]={0};
    FojAtlasRgba8Info atlas={0};
    FojAtlasDdsStatus status=FOJ_ATLAS_DDS_LOADED;
    assert(foj_atlas_dds_try_read_status(
        NULL,buf,sizeof(buf),&atlas,&status)==-1);
    assert(status==FOJ_ATLAS_DDS_INVALID_ARGUMENT);
    assert(foj_atlas_dds_try_read_status(
        "not-a-source",NULL,sizeof(buf),&atlas,&status)==-1);
    assert(status==FOJ_ATLAS_DDS_INVALID_ARGUMENT);
    assert(foj_atlas_dds_try_read_status(
        "not-a-source",buf,sizeof(buf),&atlas,NULL)==-1);
    const char *names[] = {
        "invalid arguments","optional texture absent","unsafe texture path",
        "texture read or close failed","texture changed during read",
        "unsupported or invalid DDS","classic DDS decoded"
    };
    for(int value=0;value<=6;++value)
        assert(!strcmp(foj_atlas_dds_status_name((FojAtlasDdsStatus)value),
                       names[value]));
    assert(!strcmp(foj_atlas_dds_status_name((FojAtlasDdsStatus)123),
                   "unknown DDS status"));
}
int main(void) {
    test_regular_missing_invalid_and_compat();
    test_symlinks_regular_directory_and_fifo();
    test_invalid_arguments_and_path_free_status_labels();
    puts("Stage 163 descriptor-bound DDS and path-safe diagnostics: PASS");
    return 0;
}
