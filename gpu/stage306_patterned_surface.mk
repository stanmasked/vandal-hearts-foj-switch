# Stage306 opt-in single-frame two-page BC1 1024 split-surface GPU experiment, based on Stage275 strict dynamic unsafe-topology rejection, dynamically ordered opt-in native 3-layer straight-alpha/depth GPU research NRO.
# Generated-only CI; user-local GPU bridge never distributes original PS3 assets.
OUT ?= build/foj-deko3d-stage306-split-surface
SRC := gpu/deko3d_clear_main.c gpu/three_layer_preflight.c gpu/transparency_sort.c gpu/alpha_material_contract.c gpu/alpha_pass_contract.c gpu/smoke_plan.c gpu/dksh_module.c gpu/shader_layout.c gpu/research_mesh.c gpu/research_texture.c gpu/atlas_dds.c gpu/bc1_atlas_page.c gpu/stage306_patterned_gpu_scene.c gpu/stage303_bc1_page_uv.c gpu/dds_screen_status.c gpu/dds_command_plan.c gpu/gpu_boot_diagnostics.c gpu/gpu_boot_journal.c core/gpu_vertex_stream.c core/gpu_draw_plan.c gpu/actor_upload_plan.c gpu/private_actor_bridge.c gpu/private_bundle_intake.c core/rigmesh_io.c core/material_table.c
GPU_TITLE := FoJ Patterned BC1 UV Seam Surface
GPU_VERSION := 0.32.1
GPU_EXTRA_DEPS := gpu/stage306_split_surface.mk gpu/three_layer_preflight.h gpu/transparency_sort.h gpu/alpha_material_contract.h gpu/alpha_pass_contract.h gpu/dksh_module.h gpu/shader_layout.h gpu/research_mesh.h gpu/research_texture.h gpu/atlas_dds.h gpu/bc1_atlas_page.h gpu/stage306_patterned_gpu_scene.h gpu/stage303_bc1_page_uv.h gpu/dds_screen_status.h gpu/dds_command_plan.h gpu/gpu_boot_diagnostics.h gpu/gpu_boot_journal.h core/textured_triangles.h core/gpu_draw_plan.h gpu/actor_upload_plan.h gpu/private_actor_bridge.h gpu/private_bundle_intake.h core/rigmesh_io.h core/material_table.h
GPU_METADATA_DEPS := gpu/stage306_split_surface.mk
include gpu/clear.mk

CFLAGS += -DFOJ_GPU_DRAW_TRIANGLE=1 -DFOJ_GPU_PRIVATE_BUNDLE_PREFLIGHT=1 -DFOJ_GPU_PRIVATE_ACTOR_DRAW=1 -DFOJ_GPU_DEPTH_PROOF=1 -DFOJ_GPU_ALPHA_BLEND=1 -DFOJ_GPU_THREE_LAYER_BLEND=1 -Igpu

CFLAGS += -DFOJ_GPU_STAGE306_PATTERNED_SPLIT=1
