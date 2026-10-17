#define _POSIX_C_SOURCE 200809L
/* Stage-162 generated-only replay verification tests.
 * Include the implementation in this isolated translation unit so the
 * exact internal replay routine is exercised without exporting test APIs.
 * This does NOT invoke the hardware or use PS3 game resources. */
#ifdef NDEBUG
#undef NDEBUG
#endif
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "../gpu/atlas_dds.c"

static FILE *make_stream(const uint8_t *data,size_t len) {
    FILE *file=tmpfile();
    assert(file);
    assert(fwrite(data,1,len,file)==len);
    assert(fflush(file)==0);
    return file;
}

static void test_equal_and_rewritten(void) {
    uint8_t expected[8192+11];
    for (size_t i=0;i<sizeof(expected);++i)
        expected[i]=(uint8_t)((i*17u+3u)&255u);
    FILE *fp=make_stream(expected,sizeof(expected));
    assert(verify_atlas_replay(fp,expected,sizeof(expected)));
    assert(verify_atlas_replay(fp,expected,sizeof(expected)));
    /* Same-size content change within the first 4-KiB chunk. */
    assert(fseek(fp,19,SEEK_SET)==0);
    const uint8_t rewritten=0;
    assert(fwrite(&rewritten,1,1,fp)==1);
    assert(fflush(fp)==0);
    assert(!verify_atlas_replay(fp,expected,sizeof(expected)));
    assert(fclose(fp)==0);
    /* A second change beyond one full 4-KiB block is detected too. */
    fp=make_stream(expected,sizeof(expected));
    assert(fseek(fp,6000,SEEK_SET)==0);
    const uint8_t altered=(uint8_t)(expected[6000]^0xffu);
    assert(fwrite(&altered,1,1,fp)==1);
    assert(fflush(fp)==0);
    assert(!verify_atlas_replay(fp,expected,sizeof(expected)));
    assert(fclose(fp)==0);
}

static void test_append_truncate_and_invalid_inputs(void) {
    uint8_t expected[512];
    memset(expected,0x5a,sizeof(expected));
    FILE *fp=make_stream(expected,sizeof(expected));
    assert(verify_atlas_replay(fp,expected,sizeof(expected)));
    assert(fseek(fp,0,SEEK_END)==0);
    assert(fputc(0x2a,fp)!=EOF);
    assert(fflush(fp)==0);
    assert(!verify_atlas_replay(fp,expected,sizeof(expected)));
    assert(fclose(fp)==0);
    fp=make_stream(expected,sizeof(expected)/2u);
    assert(!verify_atlas_replay(fp,expected,sizeof(expected)));
    assert(fclose(fp)==0);
    assert(!verify_atlas_replay(NULL,expected,sizeof(expected)));
    fp=make_stream(expected,sizeof(expected));
    assert(!verify_atlas_replay(fp,NULL,sizeof(expected)));
    assert(fclose(fp)==0);
}

static void test_transactional_file_failures(void) {
    const char *const filename="build/foj-stage162-native-replay.dds";
    uint8_t dds[128+256]={0};
    memcpy(dds,"DDS ",4);
    dds[4]=124;
    dds[8]=0x0f;dds[9]=0x10;
    dds[12]=8;dds[16]=8;dds[20]=32;dds[28]=1;
    dds[76]=32;dds[80]=0x41;
    dds[88]=32;dds[92]=0xff;dds[97]=0xff;dds[102]=0xff;
    dds[104]=0;dds[105]=0;dds[106]=0;dds[107]=0xff;
    dds[108]=0;dds[109]=0x10;
    /* The above minimal header is synthetic and fully deterministic. */
    FILE *fp=fopen(filename,"wb");
    assert(fp);
    assert(fwrite(dds,1,sizeof(dds),fp)==sizeof(dds));
    assert(fclose(fp)==0);
    uint8_t out[256];
    memset(out,0xa5,sizeof(out));
    FojAtlasRgba8Info info={7,9,11};
    /* Either valid native DDS or rejected: only success may modify caller. */
    const int accepted=foj_atlas_dds_try_read(filename,out,sizeof(out),&info);
    assert(accepted==1);
    assert(info.width==8 && info.height==8 && info.pixel_bytes==256);
    /* Rejection cannot touch the previously initialized metadata/pixels. */
    fp=fopen(filename,"ab");
    assert(fp);
    assert(fputc(0xdd,fp)!=EOF);
    assert(fclose(fp)==0);
    memset(out,0xa5,sizeof(out));
    info=(FojAtlasRgba8Info){7,9,11};
    assert(foj_atlas_dds_try_read(filename,out,sizeof(out),&info)==-1);
    for(size_t i=0;i<sizeof(out);++i)assert(out[i]==0xa5);
    assert(info.width==7 && info.height==9 && info.pixel_bytes==11);
    assert(remove(filename)==0);
}

int main(void) {
    test_equal_and_rewritten();
    test_append_truncate_and_invalid_inputs();
    test_transactional_file_failures();
    puts("Stage 162 native DDS same-stream replay and transaction: PASS");
    return 0;
}
