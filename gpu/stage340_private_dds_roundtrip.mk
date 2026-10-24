# Stage340: bounded private DDS -> Stage336 native upload -> GPU readback.
# The NRO contains no source image; public CI supplies a generated fixture.
OUT ?= build/foj-deko3d-stage340-private-dds-roundtrip
SRC := gpu/stage340_private_dds_roundtrip_main.c gpu/stage339_private_dds_bridge.c gpu/stage332_dds_source.c gpu/stage336_native_upload.c gpu/stage336_gpu_copy_plan.c gpu/stage335_source_staging.c
GPU_TITLE := FoJ Stage340 DDS GPU Roundtrip
GPU_VERSION := 0.42.0
GPU_EXTRA_DEPS := gpu/stage340_private_dds_roundtrip.mk gpu/stage340_private_dds_roundtrip_main.c gpu/stage339_private_dds_bridge.h gpu/stage332_dds_source.h gpu/stage336_native_upload.h gpu/stage336_gpu_copy_plan.h gpu/stage335_source_staging.h
GPU_METADATA_DEPS := gpu/stage340_private_dds_roundtrip.mk
include gpu/clear.mk
CFLAGS += -Igpu
