/*
 * Native FoJ BANIM local-pose research probe, NOT a playable game.
 * Loads an ORIGINAL .banim only from a user-controlled Switch SD card.
 * Without a local file, shows an invented single-frame test clip.
 *
 * Prints bone track-local quaternion/translation only. It does NOT apply
 * actual FoJ bone matrices, skinning, materials, camera or game rules.
 */
#include <switch.h>
#include <math.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "banim_core.h"

static void put32(uint8_t *p, uint32_t value) {
    for (int i=0;i<4;++i) p[i] = (uint8_t)(value>>(i*8));
}

static int fallback(FojAnimClip *clip) {
    uint8_t bytes[50]={0};
    bytes[0]=0x0d;
    /* 0-second duration, 1 track, one identity-pose key. */
    bytes[5]=1;
    bytes[11]=0x11;
    bytes[12]=0xff;bytes[13]=0xff;
    bytes[14]=1;
    bytes[16]=0x12;
    put32(bytes+33, UINT32_C(0x3f800000)); /* quat w = 1, at t + 16 */
    bytes[49]=0x13;
    return foj_banim_parse(bytes,sizeof(bytes),clip)==FOJ_ANIM_OK;
}

static int load_local(const char *path, FojAnimClip *clip) {
    FILE *file = fopen(path,"rb");
    if (!file) return 0;
    int okay=0;
    if (fseek(file,0,SEEK_END)==0) {
        long size=ftell(file);
        if (size>=50 && size<=FOJ_BANIM_MAX_FILE_BYTES &&
            fseek(file,0,SEEK_SET)==0) {
            uint8_t *bytes=malloc((size_t)size);
            if (bytes) {
                if (fread(bytes,1,(size_t)size,file)==(size_t)size)
                    okay=foj_banim_parse(bytes,(size_t)size,clip)==FOJ_ANIM_OK;
                free(bytes);
            }
        }
    }
    fclose(file);
    return okay;
}

int main(int argc,char **argv) {
    (void)argc;(void)argv;
    const char *path="sdmc:/switch/foj/anims/preview.banim";
    FojAnimClip clip={0};
    int loaded=load_local(path,&clip);
    if (!loaded && R_SUCCEEDED(fsdevMountSdmc()))
        loaded=load_local(path,&clip);
    if (!loaded && !fallback(&clip)) return 2;

    consoleInit(NULL);
    padConfigureInput(1,HidNpadStyleSet_NpadStandard);
    PadState pad;
    padInitializeDefault(&pad);

    size_t selected=0;
    float t=0.f;
    int playing=0;
    while (appletMainLoop()) {
        padUpdate(&pad);
        const u64 pressed=padGetButtonsDown(&pad);
        if (pressed&HidNpadButton_Plus) break;
        if ((pressed&HidNpadButton_Up) && selected>0) --selected;
        if ((pressed&HidNpadButton_Down) &&
            selected+1<clip.track_count) ++selected;
        if (pressed&HidNpadButton_A) playing=!playing;
        if (pressed&HidNpadButton_B) {playing=0;t=0;}
        if (pressed&HidNpadButton_Left) {playing=0;t-=1.f/30.f;}
        if (pressed&HidNpadButton_Right) {playing=0;t+=1.f/30.f;}
        if (playing && clip.duration>0.f) t+=1.f/60.f;
        if (t<0) t=0;
        if (t>clip.duration) t=playing ? 0.f : clip.duration;

        FojLocalPose pose={0};
        if (foj_banim_sample(&clip,t,&pose,1)==FOJ_ANIM_CAPACITY) {
            /* Reading a selected track's pose without allocating one
               whole pose array is performed directly from that track. */
            FojAnimClip one={.duration=clip.duration,.track_count=1,
                             .tracks=&clip.tracks[selected]};
            if (foj_banim_sample(&one,t,&pose,1)!=FOJ_ANIM_OK) break;
        }

        printf("\x1b[2J\x1b[H");
        printf("FOJ: BANIM native local-pose research\n");
        printf("=====================================\n");
        printf("Source: %s\n",loaded ? "USER LOCAL BANIM" : "SYNTHETIC FALLBACK");
        printf("No gameplay/PS3 engine, animation matrices or 3D rigging.\n\n");
        printf("Duration: %.4f s  Tracks: %lu\n",
               (double)clip.duration,(unsigned long)clip.track_count);
        printf("Selected: %lu  Parent: %d  Keys: %lu\n",
               (unsigned long)selected,clip.tracks[selected].parent,
               (unsigned long)clip.tracks[selected].count);
        printf("Time: %.4f s  Playing: %s\n\n",
               (double)t,playing ? "YES" : "NO");
        printf("Quaternion XYZW: % .5f % .5f % .5f % .5f\n",
               (double)pose.quat_xyzw[0],(double)pose.quat_xyzw[1],
               (double)pose.quat_xyzw[2],(double)pose.quat_xyzw[3]);
        printf("Translation XYZ: % .5f % .5f % .5f\n\n",
               (double)pose.translation_xyz[0],
               (double)pose.translation_xyz[1],
               (double)pose.translation_xyz[2]);
        printf("A play/pause, B reset\n");
        printf("D-pad LEFT/RIGHT step 1/30s\n");
        printf("D-pad UP/DOWN change bone track\n");
        printf("PLUS exit\n");
        consoleUpdate(NULL);
    }
    consoleExit(NULL);
    foj_banim_free(&clip);
    return 0;
}
