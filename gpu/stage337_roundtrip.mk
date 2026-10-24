# Isolated ROM-free GPU upload+readback NRO. Does not touch the existing renderer.
OUT ?= build/foj-deko3d-stage337-roundtrip
SRC := gpu/stage337_roundtrip_main.c gpu/stage336_native_upload.c gpu/stage336_gpu_copy_plan.c gpu/stage335_source_staging.c
GPU_TITLE := FoJ Stage337 GPU Copy Roundtrip
GPU_VERSION := 0.40.0
GPU_EXTRA_DEPS := gpu/stage337_roundtrip.mk gpu/stage337_roundtrip_main.c gpu/stage336_native_upload.h gpu/stage336_gpu_copy_plan.h gpu/stage335_source_staging.h gpu/stage332_dds_source.h
GPU_METADATA_DEPS := gpu/stage337_roundtrip.mk
include gpu/clear.mk
CFLAGS += -Igpu
