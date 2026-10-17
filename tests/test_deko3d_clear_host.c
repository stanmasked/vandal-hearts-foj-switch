/* Stateful host-only deko3d/libnx mock.
 * Includes and runs the ACTUAL optional GPU NRO entrypoint (renamed).
 * No Nintendo GPU, proprietary files or copyrighted game data.
 */
/* Keep host mock actions inside assertions active with -DNDEBUG. */
#ifdef NDEBUG
#undef NDEBUG
#endif
#include <assert.h>
#include <math.h>
#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <switch.h>
#include <deko3d.h>

#define main foj_gpu_smoke_main
#include "../gpu/deko3d_clear_main.c"
#undef main

enum {
    FAIL_NONE, FAIL_DEVICE, FAIL_QUEUE, FAIL_IMG_1, FAIL_IMG_2,
    FAIL_SWAP, FAIL_CMDMEM, FAIL_CMDBUF, FAIL_CMDLIST, FAIL_ACQUIRE,
    FAIL_PLUS, FAIL_PLUS_EARLY, FAIL_APPLET_EARLY, FAIL_VERTEX_MEM, FAIL_VERTEX_CPU, FAIL_VERTEX_GPU
};
struct FakeDevice { int tag; };
struct FakeQueue { int tag; };
struct FakeSwapchain { int tag; };
struct FakeMemBlock { int tag; void* cpu; uint32_t size; };
struct FakeCmdBuf { int tag; };

typedef struct { int slot,palette,valid; float rgba[4]; } MockList;
static struct {
    int failure,creates,frees,image_creates,block_creates;
    int submitted,presented,waited,loop_calls,acquired,cmd_added;
    int bound_slot,list_count;
    int seen_slots[2],seen_palettes[2];
    DkMemBlock vertex_buffer;
    int uploaded_vertices_verified;
    MockList lists[4];
} g;

static void reset(int failure) {
    memset(&g,0,sizeof(g));
    g.failure=failure;
    g.bound_slot=-1;
}
static void* alloc_obj(size_t size) {
    void *p=calloc(1,size);
    assert(p);
    ++g.creates;
    return p;
}
static void destroy_obj(void* p) {
    assert(p);
    ++g.frees;
    free(p);
}

void padConfigureInput(unsigned n,unsigned style) {
    assert(n==1&&style==HidNpadStyleSet_NpadStandard);
}
void padInitializeDefault(PadState* p) { assert(p); }
void padUpdate(PadState* p) { assert(p); }
u64 padGetButtonsDown(PadState* p) {
    assert(p);
    return ((g.failure==FAIL_PLUS&&g.presented==2)||
            g.failure==FAIL_PLUS_EARLY)?HidNpadButton_Plus:0;
}
int appletMainLoop(void) {
    const int limit=g.failure==FAIL_APPLET_EARLY?0:242;
    return g.loop_calls++<limit;
}
void* nwindowGetDefault(void) { return (void*)(uintptr_t)0x1234; }

void dkDeviceMakerDefaults(DkDeviceMaker* m) { m->flags=0; }
DkDevice dkDeviceCreate(const DkDeviceMaker* m) {
    /* deko3d's normal 0..1 depth is selected by *clearing* bit 8.
     * A truthiness test on the 0-valued enum was always incorrect. */
    assert((m->flags & DkDeviceFlags_DepthMinusOneToOne)==0u);
    return g.failure==FAIL_DEVICE?NULL:alloc_obj(sizeof(struct FakeDevice));
}
void dkDeviceDestroy(DkDevice d) { destroy_obj(d); }
void dkQueueMakerDefaults(DkQueueMaker* m,DkDevice d) {
    m->device=d;m->flags=0;
}
DkQueue dkQueueCreate(const DkQueueMaker* m) {
    assert(m->device&&m->flags&DkQueueFlags_Graphics);
    return g.failure==FAIL_QUEUE?NULL:alloc_obj(sizeof(struct FakeQueue));
}
void dkQueueDestroy(DkQueue q) { assert(g.waited);destroy_obj(q); }
void dkImageLayoutMakerDefaults(DkImageLayoutMaker* m,DkDevice d) {
    memset(m,0,sizeof(*m));m->device=d;
}
void dkImageLayoutInitialize(DkImageLayout* l,
                             const DkImageLayoutMaker* m) {
    assert(m->type==DkImageType_2D);
    assert(m->format==DkImageFormat_RGBA8_Unorm);
    assert(m->flags&DkImageFlags_UsageRender);
    assert(m->flags&DkImageFlags_UsagePresent);
    l->w=m->dimensions[0];l->h=m->dimensions[1];
    assert(l->w==1280&&l->h==720);
}
uint64_t dkImageLayoutGetSize(const DkImageLayout* l) {
    return (uint64_t)l->w*l->h*4+43;
}
uint32_t dkImageLayoutGetAlignment(const DkImageLayout* l) {
    assert(l->w);return 4096;
}
void dkMemBlockMakerDefaults(DkMemBlockMaker* m,DkDevice d,uint32_t size) {
    m->device=d;m->size=size;m->flags=0;
}
DkMemBlock dkMemBlockCreate(const DkMemBlockMaker* m) {
    assert(m->device);
    /* GPU-only framebuffer blocks must carry the Image flag. */
    ++g.block_creates;
    if(g.block_creates<3) {
        assert(m->flags&DkMemBlockFlags_Image);
        assert(m->size%4096==0);
        ++g.image_creates;
    } else if(g.block_creates==3) {
        assert(m->flags&DkMemBlockFlags_CpuUncached);
        assert(m->size==0x10000);
    } else {
        assert(g.block_creates==4);
        assert(m->flags&DkMemBlockFlags_CpuUncached);
        assert(m->flags&DkMemBlockFlags_GpuCached);
        assert(!(m->flags&DkMemBlockFlags_Image));
        assert(m->size==4096);
    }
    if ((g.failure==FAIL_IMG_1&&g.block_creates==1)||
        (g.failure==FAIL_IMG_2&&g.block_creates==2)||
        (g.failure==FAIL_CMDMEM&&g.block_creates==3)||
        (g.failure==FAIL_VERTEX_MEM&&g.block_creates==4))
        return NULL;
    struct FakeMemBlock* mem=alloc_obj(sizeof(struct FakeMemBlock));
    mem->size=m->size;
    if(g.block_creates==4) {
        mem->cpu=calloc(1,m->size);
        assert(mem->cpu);
        g.vertex_buffer=mem;
    }
    return mem;
}
void dkMemBlockDestroy(DkMemBlock m) {
    assert(g.waited);
    if (m==g.vertex_buffer)g.vertex_buffer=NULL;
    free(m->cpu);
    destroy_obj(m);
}
void* dkMemBlockGetCpuAddr(DkMemBlock m) {
    assert(m&&m==g.vertex_buffer);
    return g.failure==FAIL_VERTEX_CPU?NULL:m->cpu;
}
DkGpuAddr dkMemBlockGetGpuAddr(DkMemBlock m) {
    assert(m&&m==g.vertex_buffer);
    return g.failure==FAIL_VERTEX_GPU?DK_GPU_ADDR_INVALID:UINT64_C(0x7f000000);
}
void dkImageInitialize(DkImage* im,const DkImageLayout* l,
                       DkMemBlock m,uint32_t off) {
    assert(im&&l&&m&&off==0);
    im->index=(unsigned)(g.image_creates-1);
    im->memory=m;
}
void dkImageViewDefaults(DkImageView* view,const DkImage* im) {
    view->pImage=im;
}
void dkSwapchainMakerDefaults(DkSwapchainMaker* sm,DkDevice d,
                               void* window,const DkImage* const im[],
                               uint32_t count) {
    sm->device=d;sm->nativeWindow=window;
    sm->pImages=im;sm->numImages=count;
}
DkSwapchain dkSwapchainCreate(const DkSwapchainMaker* sm) {
    assert(sm->numImages==2&&sm->pImages[0]&&sm->pImages[1]);
    return g.failure==FAIL_SWAP?NULL:
        alloc_obj(sizeof(struct FakeSwapchain));
}
void dkSwapchainDestroy(DkSwapchain s) {
    assert(g.waited);destroy_obj(s);
}
void dkCmdBufMakerDefaults(DkCmdBufMaker* m,DkDevice d) {
    m->device=d;
}
DkCmdBuf dkCmdBufCreate(const DkCmdBufMaker* m) {
    assert(m->device);
    return g.failure==FAIL_CMDBUF?NULL:
        alloc_obj(sizeof(struct FakeCmdBuf));
}
void dkCmdBufDestroy(DkCmdBuf b) { assert(g.waited);destroy_obj(b); }
void dkCmdBufAddMemory(DkCmdBuf b,DkMemBlock m,
                       uint32_t off,uint32_t n) {
    assert(b&&m&&off==0&&n==0x10000);
    ++g.cmd_added;
}
void dkCmdBufBindRenderTargets(DkCmdBuf b,
    const DkImageView* const views[],uint32_t count,
    const DkImageView* depth) {
    assert(b&&views&&count==1&&depth==NULL);
    g.bound_slot=(int)views[0]->pImage->index;
    assert(g.bound_slot==0||g.bound_slot==1);
}
void dkCmdBufSetScissors(DkCmdBuf b,uint32_t first,
                           const DkScissor sc[],uint32_t count) {
    assert(b&&first==0&&count==1);
    assert(sc[0].x==0&&sc[0].y==0);
    assert(sc[0].width==1280&&sc[0].height==720);
}
void dkCmdBufClearColorFloat(DkCmdBuf b,uint32_t target,uint32_t mask,
                              float r,float green,float blue,float alpha) {
    assert(b&&target==0&&mask==DkColorMask_RGBA);
    assert(g.list_count<4);
    MockList* list=&g.lists[g.list_count];
    list->slot=g.bound_slot;
    list->rgba[0]=r;list->rgba[1]=green;
    list->rgba[2]=blue;list->rgba[3]=alpha;
    list->palette=g.list_count%2;
    list->valid=1;
    float expected[4];
    assert(foj_smoke_color((unsigned)list->palette,expected));
    for(int i=0;i<4;++i)
        assert(fabsf(list->rgba[i]-expected[i])<1e-6f);
}
DkCmdList dkCmdBufFinishList(DkCmdBuf b) {
    assert(b&&g.cmd_added);
    if(g.failure==FAIL_CMDLIST&&g.list_count==2) return 0;
    assert(g.list_count<4);
    DkCmdList list=(DkCmdList)(g.list_count+1);
    ++g.list_count;
    return list;
}
int dkQueueAcquireImage(DkQueue q,DkSwapchain s) {
    assert(q&&s);
    if(g.failure==FAIL_ACQUIRE&&g.acquired==3) return -1;
    const int slot=g.acquired%2;
    ++g.acquired;
    return slot;
}
void dkQueueSubmitCommands(DkQueue q,DkCmdList list_id) {
    assert(q&&list_id>=1&&list_id<=4);
    assert(g.vertex_buffer&&g.vertex_buffer->cpu);
    assert(!memcmp(g.vertex_buffer->cpu,kResearchTriangle,
                   sizeof(kResearchTriangle)));
    g.uploaded_vertices_verified=1;
    MockList* list=&g.lists[list_id-1];
    assert(list->valid);
    const int slot=g.submitted%2;
    const int palette=g.submitted/120%2;
    assert(list->slot==slot&&list->palette==palette);
    ++g.seen_slots[list->slot];
    ++g.seen_palettes[list->palette];
    ++g.submitted;
}
void dkQueuePresentImage(DkQueue q,DkSwapchain s,int slot) {
    assert(q&&s&&slot==g.presented%2);
    assert(g.submitted==g.presented+1);
    ++g.presented;
}
void dkQueueWaitIdle(DkQueue q) { assert(q);++g.waited; }

static void run_case(int failure,int expected_status,int frames) {
    reset(failure);
    int status=foj_gpu_smoke_main(0,NULL);
    assert(status==expected_status);
    assert(g.presented==frames);
    assert(g.creates==g.frees);
    if(failure==FAIL_NONE) {
        assert(g.list_count==4);
        assert(g.uploaded_vertices_verified);
        assert(g.presented==242);
        assert(g.seen_slots[0]==121&&g.seen_slots[1]==121);
        assert(g.seen_palettes[0]==122&&g.seen_palettes[1]==120);
    }
    printf("mock scenario %d: exit=%d frames=%d allocated=%d freed=%d\n",
           failure,status,g.presented,g.creates,g.frees);
}
int main(void) {
    run_case(FAIL_NONE,0,242);
    run_case(FAIL_DEVICE,2,0);
    run_case(FAIL_QUEUE,3,0);
    run_case(FAIL_IMG_1,3,0);
    run_case(FAIL_IMG_2,3,0);
    run_case(FAIL_SWAP,3,0);
    run_case(FAIL_CMDMEM,3,0);
    run_case(FAIL_CMDBUF,3,0);
    run_case(FAIL_CMDLIST,3,0);
    run_case(FAIL_ACQUIRE,4,3);
    run_case(FAIL_PLUS,0,2);
    run_case(FAIL_PLUS_EARLY,3,0);
    run_case(FAIL_APPLET_EARLY,3,0);
    run_case(FAIL_VERTEX_MEM,3,0);
    run_case(FAIL_VERTEX_CPU,3,0);
    run_case(FAIL_VERTEX_GPU,3,0);
    puts("Host deko3d lifecycle mock: all 16 scenarios passed");
    return 0;
}
