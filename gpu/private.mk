# Stage258 private-only preflight NRO: generated GPU quads remain unchanged.
# Private game assets MUST be supplied from a local SD and are never shipped.
# EXPERIMENTAL deko3d shader-backed multi-batch research NRO.
# Distinct output from gpu/clear.mk; existing nine CPU NROs unchanged.
# Actual UAM shader modules are loaded at runtime from the user's SD card.
# No FoJ/PS3 game resources are included.
OUT := build/foj-deko3d-private-bundle-preflight
SRC := gpu/deko3d_clear_main.c gpu/smoke_plan.c gpu/dksh_module.c gpu/shader_layout.c gpu/research_mesh.c gpu/research_texture.c gpu/atlas_dds.c gpu/dds_screen_status.c gpu/dds_command_plan.c gpu/gpu_boot_diagnostics.c gpu/gpu_boot_journal.c core/gpu_vertex_stream.c core/gpu_draw_plan.c gpu/actor_upload_plan.c gpu/private_actor_bridge.c gpu/private_bundle_intake.c core/rigmesh_io.c core/material_table.c
GPU_TITLE := FoJ Private Bundle Preflight
GPU_VERSION := 0.23.0
GPU_EXTRA_DEPS := gpu/private.mk gpu/dksh_module.h gpu/shader_layout.h gpu/research_mesh.h gpu/research_texture.h gpu/atlas_dds.h gpu/dds_screen_status.h gpu/dds_command_plan.h gpu/gpu_boot_diagnostics.h gpu/gpu_boot_journal.h core/textured_triangles.h core/gpu_draw_plan.h gpu/actor_upload_plan.h gpu/private_actor_bridge.h gpu/private_bundle_intake.h core/rigmesh_io.h core/material_table.h
GPU_METADATA_DEPS := gpu/private.mk

include gpu/clear.mk

CFLAGS += -DFOJ_GPU_DRAW_TRIANGLE=1 -DFOJ_GPU_PRIVATE_BUNDLE_PREFLIGHT=1 -Igpu

# Build-time prerequisites do not prove the original Switch SDK is installed.
# Prepare shader binaries separately: make -f gpu/Makefile triangle-verify
