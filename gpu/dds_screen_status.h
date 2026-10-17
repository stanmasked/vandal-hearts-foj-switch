#ifndef FOJ_GPU_DDS_SCREEN_STATUS_H
#define FOJ_GPU_DDS_SCREEN_STATUS_H
/* Fixed color legend for generated-only, two-slot Switch GPU DDS intake.
 * No source paths, font assets, private user bytes or PS3 game art. */
#include <stdint.h>
#include "atlas_dds.h"

enum { FOJ_GPU_DDS_STATUS_FRAMES_PER_SLOT=120 };

/* Return 1 and a solid RGBA color for every validated DDS intake status.
 * Return 0 on invalid inputs without changing the output color. */
int foj_gpu_dds_status_color(FojAtlasDdsStatus status,float rgba[4]);

/* 1: show the returned material-slot status screen; 0: regular scene.
 * On a fatal file failure, hold the last checked slot indefinitely so
 * visible errors remain accessible without console stderr. -1 invalid
 * arguments, preserving *material_slot. observed_slots is 1 or 2. */
int foj_gpu_dds_status_screen(uint64_t frame,unsigned observed_slots,
                               int fatal,unsigned *material_slot);
#endif
