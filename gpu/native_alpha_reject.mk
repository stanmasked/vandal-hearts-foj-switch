# Stage271 negative receipt opt-in native 3-layer straight-alpha/depth GPU research NRO.
# Generated-only CI; user-local GPU bridge never distributes original PS3 assets.
OUT := build/foj-deko3d-native-alpha-rejection-proof
SRC := gpu/deko3d_clear_main.c gpu/three_layer_preflight.c gpu/smoke_plan.c gpu/dksh_module.c gpu/shader_layout.c gpu/research_mesh.c gpu/research_texture.c gpu/atlas_dds.c gpu/dds_screen_status.c gpu/dds_command_plan.c gpu/gpu_boot_diagnostics.c gpu/gpu_boot_journal.c core/gpu_vertex_stream.c core/gpu_draw_plan.c gpu/actor_upload_plan.c gpu/private_actor_bridge.c gpu/private_bundle_intake.c core/rigmesh_io.c core/material_table.c
GPU_TITLE := FoJ Native Alpha Reject Research
GPU_VERSION := 0.29.1
GPU_EXTRA_DEPS := gpu/native_alpha_reject.mk gpu/three_layer_preflight.h gpu/dksh_module.h gpu/shader_layout.h gpu/research_mesh.h gpu/research_texture.h gpu/atlas_dds.h gpu/dds_screen_status.h gpu/dds_command_plan.h gpu/gpu_boot_diagnostics.h gpu/gpu_boot_journal.h core/textured_triangles.h core/gpu_draw_plan.h gpu/actor_upload_plan.h gpu/private_actor_bridge.h gpu/private_bundle_intake.h core/rigmesh_io.h core/material_table.h
GPU_METADATA_DEPS := gpu/native_alpha_reject.mk
include gpu/clear.mk

CFLAGS += -DFOJ_GPU_DRAW_TRIANGLE=1 -DFOJ_GPU_PRIVATE_BUNDLE_PREFLIGHT=1 -DFOJ_GPU_PRIVATE_ACTOR_DRAW=1 -DFOJ_GPU_DEPTH_PROOF=1 -DFOJ_GPU_ALPHA_BLEND=1 -DFOJ_GPU_THREE_LAYER_BLEND=1 -DFOJ_GPU_NATIVE_ALPHA_ORDER_GUARD=1 -DFOJ_GPU_NEGATIVE_GUEST_RECEIPT=1 -Igpu
