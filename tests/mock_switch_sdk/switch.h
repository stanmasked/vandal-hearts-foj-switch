#ifndef FOJ_HOST_SWITCH_H
#define FOJ_HOST_SWITCH_H
/* Host-only libnx subset used to exercise the real GPU smoke source.
 * This file must NEVER be placed on the actual Switch include path.
 */
#include <stdint.h>
typedef uint64_t u64;
enum { HidNpadStyleSet_NpadStandard=1, HidNpadButton_Plus=1 };
typedef struct PadState { unsigned unused; } PadState;
void padConfigureInput(unsigned players, unsigned styles);
void padInitializeDefault(PadState* pad);
void padUpdate(PadState* pad);
u64 padGetButtonsDown(PadState* pad);
int appletMainLoop(void);
void* nwindowGetDefault(void);
#endif
