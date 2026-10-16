# Minimal research-only libnx NRO. No proprietary game data or PS3 engine.
DEVKITPRO ?= /opt/devkitpro
DEVKITA64 ?= $(DEVKITPRO)/devkitA64

CC := $(DEVKITA64)/bin/aarch64-none-elf-gcc
ELF2NRO := $(DEVKITPRO)/tools/bin/elf2nro
NACPTOOL := $(DEVKITPRO)/tools/bin/nacptool

TARGET := build/foj-switch-research
ISO_TARGET := build/foj-isometric-research
COLL_TARGET := build/foj-coll-map-research
DDS_TARGET := build/foj-dds-texture-research
OBJ_TARGET := build/foj-obj-wireframe-research
OBJ_SRC := switch/source/obj_main.c core/obj_wireframe.c
DDS_SRC := switch/source/dds_main.c core/dds_texture.c
COLL_SRC := switch/source/coll_main.c core/coll_grid.c core/coll_view.c
ISO_SRC := switch/source/iso_main.c core/tactical_demo.c core/isometric_demo.c
SRC := switch/source/main.c core/tactical_demo.c
HDR := core/tactical_demo.h

CFLAGS := -O2 -g -Wall -Wextra -Werror -fPIE -ffunction-sections -fdata-sections \
    -I$(DEVKITPRO)/libnx/include -Icore
LDFLAGS := -specs=$(DEVKITPRO)/libnx/switch.specs \
    -Wl,--gc-sections -pie -L$(DEVKITPRO)/libnx/lib

.PHONY: all verify clean
all: $(TARGET).nro $(ISO_TARGET).nro $(COLL_TARGET).nro $(DDS_TARGET).nro $(OBJ_TARGET).nro

build:
	mkdir -p build

$(TARGET).elf: $(SRC) $(HDR) | build
	$(CC) $(CFLAGS) $(LDFLAGS) $(SRC) -o $@ -lnx

$(TARGET).nacp: | build
	$(NACPTOOL) --create "FoJ Switch Research" "VH FoJ contributors" "0.1.0" $@

$(TARGET).nro: $(TARGET).elf $(TARGET).nacp
	$(ELF2NRO) $< $@ --nacp=$(TARGET).nacp

$(ISO_TARGET).elf: $(ISO_SRC) $(HDR) core/isometric_demo.h | build
	$(CC) $(CFLAGS) $(LDFLAGS) $(ISO_SRC) -o $@ -lnx

$(ISO_TARGET).nacp: | build
	$(NACPTOOL) --create "FoJ Isometric Research" "VH FoJ contributors" "0.2.0" $@

$(ISO_TARGET).nro: $(ISO_TARGET).elf $(ISO_TARGET).nacp
	$(ELF2NRO) $< $@ --nacp=$(ISO_TARGET).nacp

$(COLL_TARGET).elf: $(COLL_SRC) core/coll_grid.h core/coll_view.h | build
	$(CC) $(CFLAGS) $(LDFLAGS) $(COLL_SRC) -o $@ -lnx -lm

$(COLL_TARGET).nacp: | build
	$(NACPTOOL) --create "FoJ Map Research" "VH FoJ contributors" "0.3.0" $@

$(COLL_TARGET).nro: $(COLL_TARGET).elf $(COLL_TARGET).nacp
	$(ELF2NRO) $< $@ --nacp=$(COLL_TARGET).nacp

$(DDS_TARGET).elf: $(DDS_SRC) core/dds_texture.h | build
	$(CC) $(CFLAGS) $(LDFLAGS) $(DDS_SRC) -o $@ -lnx

$(DDS_TARGET).nacp: | build
	$(NACPTOOL) --create "FoJ DDS Research" "VH FoJ contributors" "0.4.0" $@

$(DDS_TARGET).nro: $(DDS_TARGET).elf $(DDS_TARGET).nacp
	$(ELF2NRO) $< $@ --nacp=$(DDS_TARGET).nacp

$(OBJ_TARGET).elf: $(OBJ_SRC) core/obj_wireframe.h | build
	$(CC) $(CFLAGS) $(LDFLAGS) $(OBJ_SRC) -o $@ -lnx -lm

$(OBJ_TARGET).nacp: | build
	$(NACPTOOL) --create "FoJ Mesh Research" "VH FoJ contributors" "0.5.0" $@

$(OBJ_TARGET).nro: $(OBJ_TARGET).elf $(OBJ_TARGET).nacp
	$(ELF2NRO) $< $@ --nacp=$(OBJ_TARGET).nacp

verify: $(TARGET).nro $(ISO_TARGET).nro $(COLL_TARGET).nro $(DDS_TARGET).nro $(OBJ_TARGET).nro
	python3 tools/validate_nro.py $(TARGET).nro
	python3 tools/validate_nro.py $(ISO_TARGET).nro
	python3 tools/validate_nro.py $(COLL_TARGET).nro
	python3 tools/validate_nro.py $(DDS_TARGET).nro
	python3 tools/validate_nro.py $(OBJ_TARGET).nro

clean:
	rm -f $(TARGET).elf $(TARGET).nro $(TARGET).nacp \
	       $(ISO_TARGET).elf $(ISO_TARGET).nro $(ISO_TARGET).nacp \
	       $(COLL_TARGET).elf $(COLL_TARGET).nro $(COLL_TARGET).nacp \
	       $(DDS_TARGET).elf $(DDS_TARGET).nro $(DDS_TARGET).nacp \
	       $(OBJ_TARGET).elf $(OBJ_TARGET).nro $(OBJ_TARGET).nacp
