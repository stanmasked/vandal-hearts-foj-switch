/* Stage287: run the ACTUAL C 3-atlas intake on an invented local SD bundle.
 * This checker must not print private paths, hashes or decoded pixels.
 * Never interpret this as evidence of real FoJ PS3 assets or Switch runtime.
 */
#define _POSIX_C_SOURCE 200809L
#include "private_bundle_intake.h"
#include "alpha_material_contract.h"
#include <limits.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

#define FOJ_MAX_LOCAL_PATH 2048

static int make_path(char dst[FOJ_MAX_LOCAL_PATH],
                     const char *root, const char *leaf) {
    const int n=snprintf(dst,FOJ_MAX_LOCAL_PATH,"%s/%s",root,leaf);
    return n>0 && n<FOJ_MAX_LOCAL_PATH;
}

int main(int argc,char **argv) {
    if (argc!=2 || !argv[1] || !argv[1][0])
        return 2;
    char mesh[FOJ_MAX_LOCAL_PATH],material[FOJ_MAX_LOCAL_PATH];
    char d0[FOJ_MAX_LOCAL_PATH],d1[FOJ_MAX_LOCAL_PATH],d2[FOJ_MAX_LOCAL_PATH];
    if (!make_path(mesh,argv[1],"actor.fojrm") ||
        !make_path(material,argv[1],"actor.fojmat") ||
        !make_path(d0,argv[1],"material0.dds") ||
        !make_path(d1,argv[1],"material1.dds") ||
        !make_path(d2,argv[1],"material2.dds"))
        return 2;

    const char *const atlases[3]={d0,d1,d2};
    const FojTextureCamera cam={0.f,0.f,0.f,2.f,0.f,0.f,1.f,0.f};
    FojGpuPrivateBundleData bound={0};
    const FojGpuPrivateBundleStatus result=foj_gpu_private_bundle_load(
        mesh,material,atlases,&cam,1280u,720u,4096u,&bound);
    int good=(result==FOJ_PRIVATE_BUNDLE_OK);
    if (good) {
        good=(bound.report.actor.stream.vertices_written==9u &&
              bound.report.actor.stream.batches_written==3u &&
              bound.report.actor.upload.material_mask==7u &&
              bound.report.atlas_count==3u &&
              bound.vertices!=NULL && bound.batches!=NULL);
        for (unsigned i=0;good && i<3u;++i) {
            if (!bound.rgba[i] ||
                bound.batches[i].first_vertex!=3u*i ||
                bound.batches[i].vertex_count!=3u ||
                bound.batches[i].texture_index!=i ||
                bound.report.atlas[i].width!=64u ||
                bound.report.atlas[i].height!=64u ||
                bound.report.atlas[i].pixel_bytes!=64u*64u*4u)
                good=0;
        }
        if (good) {
            /* These exact RGBA values are from synthetic Python constants
             * VIOLET/WARM/COOL, not derived from any PS3 resource. */
            static const uint8_t colors[3][4]={
                {96,72,201,128},{232,55,28,128},{21,202,219,255}
            };
            for (unsigned i=0;good && i<3u;++i)
                if (memcmp(bound.rgba[i],colors[i],4)!=0)
                    good=0;
        }
        if (good && !foj_gpu_opaque_rear_atlas(
                bound.rgba[2],&bound.report.atlas[2]))
            good=0;
    }
    foj_gpu_private_bundle_free(&bound);
    if (!good) {
        fputs("Stage287 native three-atlas binding rejected\n",stderr);
        return 1;
    }
    puts("STAGE287_ACTUAL_C_THREE_ATLAS_BINDING_PASS");
    return 0;
}
