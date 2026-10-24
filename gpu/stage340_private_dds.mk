# Stage340: owner-local DDS -> Stage332/339 decode -> Stage336 GPU upload -> fullscreen sampling.
# CI and NeXium use a generated fixture only; original DDS bytes never enter Actions.
OUT ?= build/foj-deko3d-stage340-private-dds
SRC := gpu/stage340_private_dds_main.c gpu/stage332_dds_source.c gpu/stage339_private_dds_bridge.c gpu/stage335_source_staging.c gpu/stage336_gpu_copy_plan.c gpu/stage336_native_upload.c gpu/smoke_plan.c gpu/dksh_module.c gpu/shader_layout.c gpu/research_mesh.c gpu/research_texture.c gpu/atlas_dds.c gpu/dds_screen_status.c gpu/dds_command_plan.c gpu/gpu_boot_diagnostics.c gpu/gpu_boot_journal.c core/gpu_vertex_stream.c core/gpu_draw_plan.c gpu/actor_upload_plan.c
GPU_TITLE := FoJ Stage340 Private DDS GPU Sample
GPU_VERSION := 0.42.0
GPU_EXTRA_DEPS := gpu/stage340_private_dds_main.c gpu/stage340_private_dds.mk gpu/stage332_dds_source.h gpu/stage339_private_dds_bridge.h gpu/stage335_source_staging.h gpu/stage336_gpu_copy_plan.h gpu/stage336_native_upload.h gpu/smoke_plan.h gpu/deko3d_api_contract.h gpu/dksh_module.h gpu/shader_layout.h gpu/research_mesh.h gpu/research_texture.h gpu/atlas_dds.h gpu/dds_screen_status.h gpu/dds_command_plan.h gpu/gpu_boot_diagnostics.h gpu/gpu_boot_journal.h core/gpu_vertex_stream.h core/gpu_draw_plan.h gpu/actor_upload_plan.h core/textured_triangles.h
GPU_METADATA_DEPS := gpu/stage340_private_dds.mk
include gpu/clear.mk

CFLAGS += -DFOJ_GPU_DRAW_TRIANGLE=1 -DFOJ_GPU_STAGE340_PRIVATE_DDS_TEXTURE=1 -Igpu
