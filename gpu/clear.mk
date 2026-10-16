# Optional first deko3d GPU clear-and-present smoke-test NRO.
# This is deliberately SEPARATE from switch/Makefile's nine existing NROs.
# Requires devkitA64, libnx and deko3d from devkitPro switch-dev.
DEVKITPRO ?= /opt/devkitpro
# Debug deko3d includes API validation; select deko3d for final release.
GPU_LIB ?= deko3dd
DEVKITA64 ?= $(DEVKITPRO)/devkitA64
CC := $(DEVKITA64)/bin/aarch64-none-elf-gcc
ELF2NRO := $(DEVKITPRO)/tools/bin/elf2nro
NACPTOOL := $(DEVKITPRO)/tools/bin/nacptool
OUT := build/foj-deko3d-clear-smoke
SRC := gpu/deko3d_clear_main.c

CFLAGS := -std=c11 -O2 -Wall -Wextra -Werror -fPIE -ffunction-sections \
  -fdata-sections -I$(DEVKITPRO)/libnx/include
LDFLAGS := -specs=$(DEVKITPRO)/libnx/switch.specs -Wl,--gc-sections \
  -pie -L$(DEVKITPRO)/libnx/lib

.PHONY: all verify clean preflight
all: $(OUT).nro

preflight:
	@test -x "$(CC)" || { echo "Missing devkitA64 cross-compiler" >&2; exit 2; }
	@test -f "$(DEVKITPRO)/libnx/include/deko3d.h" || { echo "Missing deko3d.h from switch-dev" >&2; exit 2; }
	@test -f "$(DEVKITPRO)/libnx/lib/lib$(GPU_LIB).a" || { echo "Missing libdeko3d.a" >&2; exit 2; }

build:
	mkdir -p build

$(OUT).elf: $(SRC) | build preflight
	$(CC) $(CFLAGS) $(LDFLAGS) $(SRC) -o $@ -l$(GPU_LIB) -lnx -lm

$(OUT).nacp: | build
	$(NACPTOOL) --create "FoJ GPU Clear Smoke" "VH FoJ contributors" "0.10.0" $@

$(OUT).nro: $(OUT).elf $(OUT).nacp
	$(ELF2NRO) $< $@ --nacp=$(OUT).nacp

verify: $(OUT).nro
	python3 tools/validate_nro.py $(OUT).nro

clean:
	rm -f $(OUT).elf $(OUT).nacp $(OUT).nro
