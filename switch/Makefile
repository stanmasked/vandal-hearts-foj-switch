# Minimal research-only libnx NRO. No proprietary game data or PS3 engine.
DEVKITPRO ?= /opt/devkitpro
DEVKITA64 ?= $(DEVKITPRO)/devkitA64

CC := $(DEVKITA64)/bin/aarch64-none-elf-gcc
ELF2NRO := $(DEVKITPRO)/tools/bin/elf2nro
NACPTOOL := $(DEVKITPRO)/tools/bin/nacptool

TARGET := build/foj-switch-research
SRC := switch/source/main.c core/tactical_demo.c
HDR := core/tactical_demo.h

CFLAGS := -O2 -g -Wall -Wextra -Werror -fPIE -ffunction-sections -fdata-sections \
    -I$(DEVKITPRO)/libnx/include -Icore
LDFLAGS := -specs=$(DEVKITPRO)/libnx/switch.specs \
    -Wl,--gc-sections -pie -L$(DEVKITPRO)/libnx/lib

.PHONY: all verify clean
all: $(TARGET).nro

build:
	mkdir -p build

$(TARGET).elf: $(SRC) $(HDR) | build
	$(CC) $(CFLAGS) $(LDFLAGS) $(SRC) -o $@ -lnx

$(TARGET).nacp: | build
	$(NACPTOOL) --create "FoJ Switch Research" "VH FoJ contributors" "0.1.0" $@

$(TARGET).nro: $(TARGET).elf $(TARGET).nacp
	$(ELF2NRO) $< $@ --nacp=$(TARGET).nacp

verify: $(TARGET).nro
	python3 tools/validate_nro.py $(TARGET).nro

clean:
	rm -f $(TARGET).elf $(TARGET).nro $(TARGET).nacp
