# Stage341: owner-local DDS -> Stage336 native upload -> fragment shader -> framebuffer.
# The NRO contains no source pixels. Public CI supplies a generated BGRA8 DDS only.
OUT ?= build/foj-deko3d-stage341-private-dds-frame
SRC := gpu/deko3d_clear_main.c gpu/stage332_dds_source.c gpu/stage336_native_upload.c gpu/stage336_gpu_copy_plan.c gpu/stage335_source_staging.c gpu/smoke_plan.c gpu/dksh_module.c gpu/shader_layout.c gpu/research_texture.c gpu/atlas_dds.c gpu/dds_screen_status.c gpu/dds_command_plan.c gpu/gpu_boot_diagnostics.c gpu/gpu_boot_journal.c gpu/stage318_triangle_uv_coverage.c gpu/stage319_bilinear_halo_support.c gpu/stage320_uv_page_batches.c gpu/stage321_three_slot_plan.c gpu/stage322_bounded_corner_tile.c gpu/stage324_corner_tile_clip.c gpu/stage325_corner_tile_partition.c gpu/stage327_ordered_partition_stream.c gpu/stage328_atomic_corner_patch_stream.c core/gpu_vertex_stream.c core/gpu_draw_plan.c gpu/actor_upload_plan.c
GPU_TITLE := FoJ Stage341 Private DDS Frame
GPU_VERSION := 0.43.0
GPU_EXTRA_DEPS := gpu/stage341_private_dds_frame.mk gpu/stage332_dds_source.h gpu/stage336_native_upload.h gpu/stage336_gpu_copy_plan.h gpu/stage335_source_staging.h gpu/stage332_dds_source.h gpu/smoke_plan.h gpu/deko3d_api_contract.h gpu/dksh_module.h gpu/shader_layout.h gpu/research_mesh.h gpu/research_texture.h gpu/atlas_dds.h gpu/dds_screen_status.h gpu/dds_command_plan.h gpu/gpu_boot_diagnostics.h gpu/gpu_boot_journal.h gpu/stage318_triangle_uv_coverage.h gpu/stage319_bilinear_halo_support.h gpu/stage320_uv_page_batches.h gpu/stage321_three_slot_plan.h gpu/stage322_bounded_corner_tile.h gpu/stage324_corner_tile_clip.h gpu/stage325_corner_tile_partition.h gpu/stage327_ordered_partition_stream.h gpu/stage328_atomic_corner_patch_stream.h core/gpu_vertex_stream.h core/gpu_draw_plan.h gpu/actor_upload_plan.h core/textured_triangles.h
GPU_METADATA_DEPS := gpu/stage341_private_dds_frame.mk
include gpu/clear.mk

CFLAGS += -DFOJ_GPU_DRAW_TRIANGLE=1 -DFOJ_GPU_STAGE341_PRIVATE_DDS_DRAW=1 -Igpu
