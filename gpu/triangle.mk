# EXPERIMENTAL deko3d shader-backed multi-batch research NRO.
# Distinct output from gpu/clear.mk; existing nine CPU NROs unchanged.
# Actual UAM shader modules are loaded at runtime from the user's SD card.
# No FoJ/PS3 game resources are included.
OUT := build/foj-deko3d-triangle-research
SRC := gpu/deko3d_clear_main.c gpu/smoke_plan.c gpu/dksh_module.c gpu/shader_layout.c gpu/research_mesh.c gpu/research_texture.c gpu/atlas_dds.c gpu/dds_screen_status.c core/gpu_vertex_stream.c core/gpu_draw_plan.c
GPU_TITLE := FoJ GPU Triangle Research
GPU_VERSION := 0.18.0
GPU_EXTRA_DEPS := gpu/triangle.mk gpu/dksh_module.h gpu/shader_layout.h gpu/research_mesh.h gpu/research_texture.h gpu/atlas_dds.h gpu/dds_screen_status.h core/textured_triangles.h core/gpu_draw_plan.h
GPU_METADATA_DEPS := gpu/triangle.mk

include gpu/clear.mk

CFLAGS += -DFOJ_GPU_DRAW_TRIANGLE=1 -Igpu

# Build-time prerequisites do not prove the original Switch SDK is installed.
# Prepare shader binaries separately: make -f gpu/Makefile triangle-verify
