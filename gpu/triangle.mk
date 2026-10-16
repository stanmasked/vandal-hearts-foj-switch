# EXPERIMENTAL deko3d shader-backed 3-vertex NRO.
# Distinct output from gpu/clear.mk; existing nine CPU NROs unchanged.
# Actual UAM shader modules are loaded at runtime from the user's SD card.
# No FoJ/PS3 game resources are included.
OUT := build/foj-deko3d-triangle-research
SRC := gpu/deko3d_clear_main.c gpu/smoke_plan.c gpu/dksh_module.c
GPU_TITLE := FoJ GPU Triangle Research
GPU_VERSION := 0.11.0

include gpu/clear.mk

CFLAGS += -DFOJ_GPU_DRAW_TRIANGLE=1 -Igpu

# Build-time prerequisites do not prove the original Switch SDK is installed.
# Prepare shader binaries separately: make -f gpu/Makefile triangle-verify
