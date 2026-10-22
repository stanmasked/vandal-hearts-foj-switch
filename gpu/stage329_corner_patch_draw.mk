# Stage329: native deko3d draw of the Stage328 generated-only corner patch.
# The scene uses synthetic RGBA8 pages and never reads user or original game data.
OUT ?= build/foj-deko3d-stage329-corner-patch
SRC := gpu/deko3d_clear_main.c gpu/smoke_plan.c gpu/dksh_module.c gpu/shader_layout.c gpu/research_texture.c gpu/atlas_dds.c gpu/dds_screen_status.c gpu/dds_command_plan.c gpu/gpu_boot_diagnostics.c gpu/gpu_boot_journal.c gpu/stage318_triangle_uv_coverage.c gpu/stage319_bilinear_halo_support.c gpu/stage320_uv_page_batches.c gpu/stage321_three_slot_plan.c gpu/stage322_bounded_corner_tile.c gpu/stage324_corner_tile_clip.c gpu/stage325_corner_tile_partition.c gpu/stage327_ordered_partition_stream.c gpu/stage328_atomic_corner_patch_stream.c core/gpu_vertex_stream.c core/gpu_draw_plan.c gpu/actor_upload_plan.c
GPU_TITLE := FoJ Stage329 Corner Patch Draw
GPU_VERSION := 0.38.0
GPU_EXTRA_DEPS := gpu/stage329_corner_patch_draw.mk gpu/smoke_plan.h gpu/deko3d_api_contract.h gpu/dksh_module.h gpu/shader_layout.h gpu/research_mesh.h gpu/research_texture.h gpu/atlas_dds.h gpu/dds_screen_status.h gpu/dds_command_plan.h gpu/gpu_boot_diagnostics.h gpu/gpu_boot_journal.h gpu/stage318_triangle_uv_coverage.h gpu/stage319_bilinear_halo_support.h gpu/stage320_uv_page_batches.h gpu/stage321_three_slot_plan.h gpu/stage322_bounded_corner_tile.h gpu/stage324_corner_tile_clip.h gpu/stage325_corner_tile_partition.h gpu/stage327_ordered_partition_stream.h gpu/stage328_atomic_corner_patch_stream.h core/gpu_vertex_stream.h core/gpu_draw_plan.h gpu/actor_upload_plan.h core/textured_triangles.h
GPU_METADATA_DEPS := gpu/stage329_corner_patch_draw.mk
include gpu/clear.mk

CFLAGS += -DFOJ_GPU_DRAW_TRIANGLE=1 -DFOJ_GPU_STAGE329_PATCH_STREAM=1 -DFOJ_GPU_STAGE309_LINEAR_GUTTER=1 -Igpu
