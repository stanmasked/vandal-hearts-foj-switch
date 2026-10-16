#ifndef FOJ_HOST_DEKO3D_H
#define FOJ_HOST_DEKO3D_H
/* TEST-ONLY declarations checked against public deko3d C signatures.
 * Numeric enums are pinned to upstream devkitPro/deko3d deko3d.h and
 * cross-checked separately during optional real toolchain preflight.
 * A small mock contract, NOT the SDK and NOT for compiling a real NRO.
 */
#include <stdint.h>
#include <stddef.h>
typedef struct FakeDevice* DkDevice;
typedef struct FakeQueue* DkQueue;
typedef struct FakeCmdBuf* DkCmdBuf;
typedef struct FakeSwapchain* DkSwapchain;
typedef struct FakeMemBlock* DkMemBlock;
typedef uintptr_t DkCmdList;
typedef uint64_t DkGpuAddr;
#define DK_GPU_ADDR_INVALID UINT64_MAX
typedef struct { unsigned index; DkMemBlock memory; } DkImage;
typedef struct { const DkImage* pImage; } DkImageView;
typedef struct { uint32_t x,y,width,height; } DkScissor;
typedef struct { uint32_t flags; } DkDeviceMaker;
typedef struct { DkDevice device; uint32_t flags; } DkQueueMaker;
typedef struct { DkDevice device; uint32_t flags,size; } DkMemBlockMaker;
typedef struct { DkDevice device; } DkCmdBufMaker;
typedef struct {
    DkDevice device; uint32_t flags,format,type,dimensions[3];
} DkImageLayoutMaker;
typedef struct { uint32_t w,h; } DkImageLayout;
typedef struct {
    DkDevice device; void* nativeWindow;
    const DkImage* const* pImages; uint32_t numImages;
} DkSwapchainMaker;
enum {
    DkDeviceFlags_DepthZeroToOne=256,
    DkDeviceFlags_OriginUpperLeft=0, DkDeviceFlags_YAxisPointsUp=0,
    DkQueueFlags_Graphics=1, DkImageType_2D=2,
    DkImageFormat_RGBA8_Unorm=28,
    DkImageFlags_UsageRender=256, DkImageFlags_UsagePresent=1024,
    DkMemBlockFlags_GpuCached=8, DkMemBlockFlags_Image=32,
    DkMemBlockFlags_CpuUncached=1,
    DkColorMask_RGBA=15, DK_MEMBLOCK_ALIGNMENT=4096
};
void dkDeviceMakerDefaults(DkDeviceMaker*);
DkDevice dkDeviceCreate(const DkDeviceMaker*);
void dkDeviceDestroy(DkDevice);
void dkQueueMakerDefaults(DkQueueMaker*,DkDevice);
DkQueue dkQueueCreate(const DkQueueMaker*);
void dkQueueDestroy(DkQueue);
void dkImageLayoutMakerDefaults(DkImageLayoutMaker*,DkDevice);
void dkImageLayoutInitialize(DkImageLayout*,const DkImageLayoutMaker*);
uint64_t dkImageLayoutGetSize(const DkImageLayout*);
uint32_t dkImageLayoutGetAlignment(const DkImageLayout*);
void dkMemBlockMakerDefaults(DkMemBlockMaker*,DkDevice,uint32_t);
DkMemBlock dkMemBlockCreate(const DkMemBlockMaker*);
void dkMemBlockDestroy(DkMemBlock);
void* dkMemBlockGetCpuAddr(DkMemBlock);
DkGpuAddr dkMemBlockGetGpuAddr(DkMemBlock);
void dkImageInitialize(DkImage*,const DkImageLayout*,DkMemBlock,uint32_t);
void dkImageViewDefaults(DkImageView*,const DkImage*);
void dkSwapchainMakerDefaults(
    DkSwapchainMaker*,DkDevice,void*,const DkImage* const[],uint32_t);
DkSwapchain dkSwapchainCreate(const DkSwapchainMaker*);
void dkSwapchainDestroy(DkSwapchain);
void dkCmdBufMakerDefaults(DkCmdBufMaker*,DkDevice);
DkCmdBuf dkCmdBufCreate(const DkCmdBufMaker*);
void dkCmdBufDestroy(DkCmdBuf);
void dkCmdBufAddMemory(DkCmdBuf,DkMemBlock,uint32_t,uint32_t);
void dkCmdBufBindRenderTargets(
    DkCmdBuf,const DkImageView* const[],uint32_t,const DkImageView*);
void dkCmdBufSetScissors(DkCmdBuf,uint32_t,const DkScissor[],uint32_t);
void dkCmdBufClearColorFloat(
    DkCmdBuf,uint32_t,uint32_t,float,float,float,float);
DkCmdList dkCmdBufFinishList(DkCmdBuf);
void dkQueueSubmitCommands(DkQueue,DkCmdList);
void dkQueuePresentImage(DkQueue,DkSwapchain,int);
int dkQueueAcquireImage(DkQueue,DkSwapchain);
void dkQueueWaitIdle(DkQueue);
#endif
