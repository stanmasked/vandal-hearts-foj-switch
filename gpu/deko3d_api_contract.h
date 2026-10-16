#ifndef FOJ_DEKO3D_API_CONTRACT_H
#define FOJ_DEKO3D_API_CONTRACT_H

/* Compile-time assertions on the small set of upstream deko3d ABI
 * constants used by FoJ's OPTIONAL first-clear NRO.
 *
 * Include <deko3d.h> before this header. In the real devkitPro NRO build
 * these checks compare against the actual installed SDK, never the host
 * mock. The mock runs the same checks and must stay numerically identical.
 *
 * Pinned against devkitPro/deko3d include/deko3d.h (Oct 2026).
 */
#include <stdint.h>
/* 0-to-1 depth is selected by CLEARING bit 8. Setting bit 8 instead
 * selects the incompatible -1-to-1 clip-depth convention. */
_Static_assert(DkDeviceFlags_DepthZeroToOne == 0u,
               "deko3d 0..1 clip-depth flag must be zero");
_Static_assert(DkDeviceFlags_DepthMinusOneToOne == 256u,
               "deko3d -1..1 clip-depth flag must set bit 8");
_Static_assert(DkImageType_2D == 2, "unexpected 2D image enum");
_Static_assert(DkImageFormat_RGBA8_Unorm == 28,
               "wrong RGBA8 render target enum");
_Static_assert(DkImageFlags_UsageRender == 256u,
               "wrong render target image bit");
_Static_assert(DkImageFlags_UsagePresent == 1024u,
               "wrong swapchain present image bit");
_Static_assert(DkMemBlockFlags_GpuCached == 8u,
               "wrong GPU cached memory bit");
_Static_assert(DkMemBlockFlags_Image == 32u,
               "wrong GPU image memory bit");
_Static_assert(DkColorMask_RGBA == 15u,
               "wrong color channel clear mask");
_Static_assert(DK_MEMBLOCK_ALIGNMENT == 4096u,
               "unexpected GPU memory alignment");
_Static_assert(DK_GPU_ADDR_INVALID == UINT64_MAX,
               "deko3d invalid GPU address sentinel must be UINT64_MAX");
_Static_assert(sizeof(DkGpuAddr) == sizeof(uint64_t),
               "deko3d GPU address requires a 64-bit type");

/* Verify the GPU smoke clear color is actually visible and returned with
 * the right alpha; using these constants does NOT establish GPU output. */
#endif
