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

/* Triangle-mode API declarations: compile-time only in host-triangle-check.
 * No shader instructions or fake GPU frame are produced. These structures
 * mirror the public field names/initializers required by the NRO source. */
typedef struct { unsigned char opaque[128]; } DkShader;
typedef struct {
    DkMemBlock codeMem;
    const void *control;
    uint32_t codeOffset, programId;
} DkShaderMaker;
typedef enum { DkStage_Vertex=0, DkStage_Fragment=4 } DkStage;
enum { DkStageFlag_GraphicsMask=31u };
typedef struct { float x,y,width,height,near,far; } DkViewport;
typedef struct { uint32_t dummy; } DkRasterizerState;
typedef struct { uint32_t dummy; } DkColorState;
typedef struct { uint32_t masks; } DkColorWriteState;
typedef enum {
    DkVtxAttribSize_4x32=1,
    DkVtxAttribSize_2x32=4
} DkVtxAttribSize;
typedef enum { DkVtxAttribType_Float=7 } DkVtxAttribType;
typedef struct {
    uint32_t bufferId:5;
    uint32_t :1;
    uint32_t isFixed:1;
    uint32_t offset:14;
    DkVtxAttribSize size:6;
    DkVtxAttribType type:3;
    uint32_t :1;
    uint32_t isBgra:1;
} DkVtxAttribState;
typedef struct { uint32_t stride,divisor; } DkVtxBufferState;
typedef struct { DkGpuAddr addr; uint32_t size; } DkBufExtents;
enum { DkPrimitive_Triangles=4, DkMemBlockFlags_Code=16 };
void dkShaderMakerDefaults(DkShaderMaker*,DkMemBlock,uint32_t);
void dkShaderInitialize(DkShader*,const DkShaderMaker*);
int dkShaderIsValid(const DkShader*);
DkStage dkShaderGetStage(const DkShader*);
void dkRasterizerStateDefaults(DkRasterizerState*);
void dkColorStateDefaults(DkColorState*);
void dkColorWriteStateDefaults(DkColorWriteState*);
void dkCmdBufSetViewports(DkCmdBuf,uint32_t,const DkViewport*,uint32_t);
void dkCmdBufBindShaders(DkCmdBuf,uint32_t,const DkShader* const*,uint32_t);
void dkCmdBufBindRasterizerState(DkCmdBuf,const DkRasterizerState*);
void dkCmdBufBindColorState(DkCmdBuf,const DkColorState*);
void dkCmdBufBindColorWriteState(DkCmdBuf,const DkColorWriteState*);
void dkCmdBufBindVtxAttribState(DkCmdBuf,const DkVtxAttribState*,uint32_t);
void dkCmdBufBindVtxBufferState(DkCmdBuf,const DkVtxBufferState*,uint32_t);
void dkCmdBufBindVtxBuffers(DkCmdBuf,uint32_t,const DkBufExtents*,uint32_t);
void dkCmdBufDraw(DkCmdBuf,uint32_t,uint32_t,uint32_t,uint32_t,uint32_t);
#endif
