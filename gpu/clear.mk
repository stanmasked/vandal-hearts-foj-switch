# Optional first deko3d GPU clear-and-present smoke-test NRO.
# This is deliberately SEPARATE from switch/Makefile's nine existing NROs.
# Requires devkitA64, libnx and deko3d from devkitPro switch-dev.
DEVKITPRO ?= /opt/devkitpro
# Debug deko3d includes API validation; select deko3d for final release.
GPU_LIB ?= deko3dd
GPU_TITLE ?= FoJ GPU Clear Smoke
GPU_VERSION ?= 0.10.0
HOSTCC ?= cc
HOST_ABI := build/foj-deko3d-contract-host
HOST_ABI_SAN := build/foj-deko3d-contract-asan
HOST_TEST := build/foj-gpu-smoke-plan-host
HOST_TEST_SAN := build/foj-gpu-smoke-plan-asan
HOST_MOCK := build/foj-deko3d-lifecycle-host
HOST_MOCK_SAN := build/foj-deko3d-lifecycle-asan
HOST_SHADERS := build/foj-deko3d-shader-layout-host
HOST_SHADERS_SAN := build/foj-deko3d-shader-layout-asan
HOST_DKSH := build/foj-dksh-intake-host
HOST_DKSH_SAN := build/foj-dksh-intake-asan
HOST_DKSH_INTEGRATION := build/foj-dksh-layout-integration
HOST_DKSH_INTEGRATION_SAN := build/foj-dksh-layout-integration-asan
DEVKITA64 ?= $(DEVKITPRO)/devkitA64
CC := $(DEVKITA64)/bin/aarch64-none-elf-gcc
ELF2NRO := $(DEVKITPRO)/tools/bin/elf2nro
NACPTOOL := $(DEVKITPRO)/tools/bin/nacptool
OUT ?= build/foj-deko3d-clear-smoke
SRC ?= gpu/deko3d_clear_main.c gpu/smoke_plan.c
GPU_EXTRA_DEPS ?=

CFLAGS := -std=c11 -O2 -Wall -Wextra -Werror -fPIE -ffunction-sections \
  -fdata-sections -I$(DEVKITPRO)/libnx/include -Icore
LDFLAGS := -specs=$(DEVKITPRO)/libnx/switch.specs -Wl,--gc-sections \
  -pie -L$(DEVKITPRO)/libnx/lib

.PHONY: all verify clean preflight host-check host-mock-sanitized host-triangle-check
all: $(OUT).nro

preflight:
	@test -x "$(CC)" || { echo "Missing devkitA64 cross-compiler" >&2; exit 2; }
	@test -f "$(DEVKITPRO)/libnx/include/deko3d.h" || { echo "Missing deko3d.h from switch-dev" >&2; exit 2; }
	@test -f "$(DEVKITPRO)/libnx/lib/lib$(GPU_LIB).a" || { echo "Missing lib$(GPU_LIB).a" >&2; exit 2; }

build:
	mkdir -p build

# Run this independently from devkitPro, UAM or a Nintendo Switch.
$(HOST_TEST): tests/test_gpu_smoke_plan.c gpu/smoke_plan.c gpu/smoke_plan.h core/gpu_vertex_stream.h | build
	$(HOSTCC) -std=c11 -Wall -Wextra -Werror -pedantic -Igpu \
	  tests/test_gpu_smoke_plan.c gpu/smoke_plan.c -lm -o $@

$(HOST_ABI): tests/test_deko3d_api_contract.c \
            tests/mock_switch_sdk/deko3d.h gpu/deko3d_api_contract.h | build
	$(HOSTCC) -std=c11 -Wall -Wextra -Werror -pedantic \
	  -Itests/mock_switch_sdk -Igpu -Icore \
	  tests/test_deko3d_api_contract.c -o $@

# Exercise allocation/palette and API-contract checks under sanitizers too.
$(HOST_TEST_SAN): tests/test_gpu_smoke_plan.c gpu/smoke_plan.c gpu/smoke_plan.h core/gpu_vertex_stream.h | build
	$(HOSTCC) -std=c11 -O1 -g -Wall -Wextra -Werror -pedantic \
	  -fsanitize=address,undefined -fno-omit-frame-pointer -Igpu \
	  tests/test_gpu_smoke_plan.c gpu/smoke_plan.c -lm -o $@

$(HOST_ABI_SAN): tests/test_deko3d_api_contract.c tests/mock_switch_sdk/deko3d.h gpu/deko3d_api_contract.h | build
	$(HOSTCC) -std=c11 -O1 -g -Wall -Wextra -Werror -pedantic \
	  -fsanitize=address,undefined -fno-omit-frame-pointer \
	  -Itests/mock_switch_sdk -Igpu -Icore \
	  tests/test_deko3d_api_contract.c -o $@

$(HOST_SHADERS): tests/test_shader_layout.c gpu/shader_layout.c \
                 gpu/shader_layout.h | build
	$(HOSTCC) -std=c11 -Wall -Wextra -Werror -pedantic -Igpu \
	  tests/test_shader_layout.c gpu/shader_layout.c -o $@

$(HOST_SHADERS_SAN): tests/test_shader_layout.c gpu/shader_layout.c \
                     gpu/shader_layout.h | build
	$(HOSTCC) -std=c11 -O1 -g -fsanitize=address,undefined \
	  -fno-omit-frame-pointer -Igpu \
	  tests/test_shader_layout.c gpu/shader_layout.c -o $@

# Verify transactional DKSH intake using generated-only modules.
$(HOST_DKSH): tests/test_dksh_module.c gpu/dksh_module.c \
              gpu/dksh_module.h | build
	$(HOSTCC) -std=c11 -Wall -Wextra -Werror -pedantic -Igpu \
	  tests/test_dksh_module.c gpu/dksh_module.c -o $@

$(HOST_DKSH_SAN): tests/test_dksh_module.c gpu/dksh_module.c \
                  gpu/dksh_module.h | build
	$(HOSTCC) -std=c11 -O1 -g -Wall -Wextra -Werror -pedantic \
	  -fsanitize=address,undefined -fno-omit-frame-pointer -Igpu \
	  tests/test_dksh_module.c gpu/dksh_module.c -o $@

$(HOST_DKSH_INTEGRATION): tests/test_gpu_dksh_integration.c gpu/dksh_module.c gpu/shader_layout.c gpu/dksh_module.h gpu/shader_layout.h | build
	$(HOSTCC) -std=c11 -Wall -Wextra -Werror -pedantic -Igpu tests/test_gpu_dksh_integration.c gpu/dksh_module.c gpu/shader_layout.c -o $@

$(HOST_DKSH_INTEGRATION_SAN): tests/test_gpu_dksh_integration.c gpu/dksh_module.c gpu/shader_layout.c gpu/dksh_module.h gpu/shader_layout.h | build
	$(HOSTCC) -std=c11 -O1 -g -Wall -Wextra -Werror -pedantic -fsanitize=address,undefined -fno-omit-frame-pointer -Igpu tests/test_gpu_dksh_integration.c gpu/dksh_module.c gpu/shader_layout.c -o $@

$(HOST_MOCK): tests/test_deko3d_clear_host.c tests/mock_switch_sdk/deko3d.h \
              tests/mock_switch_sdk/switch.h gpu/deko3d_clear_main.c \
              gpu/smoke_plan.c gpu/smoke_plan.h core/gpu_vertex_stream.h | build
	$(HOSTCC) -std=c11 -O1 -g -Wall -Wextra -Werror -pedantic \
	  -Itests/mock_switch_sdk -Igpu -Icore \
	  tests/test_deko3d_clear_host.c gpu/smoke_plan.c -lm -o $@

$(HOST_MOCK_SAN): tests/test_deko3d_clear_host.c tests/mock_switch_sdk/deko3d.h \
                  tests/mock_switch_sdk/switch.h gpu/deko3d_clear_main.c \
                  gpu/smoke_plan.c gpu/smoke_plan.h core/gpu_vertex_stream.h | build
	$(HOSTCC) -std=c11 -O1 -g -Wall -Wextra -Werror -pedantic \
	  -fsanitize=address,undefined -fno-omit-frame-pointer \
	  -Itests/mock_switch_sdk -Igpu -Icore \
	  tests/test_deko3d_clear_host.c gpu/smoke_plan.c -lm -o $@

# Check the real optional triangle source in GCC/Clang C11 syntax mode.
# This uses lightweight SDK declarations and DOES NOT link or run GPU code.
host-triangle-check:
	$(HOSTCC) -std=c11 -Wall -Wextra -Werror -pedantic \
	  -DFOJ_GPU_DRAW_TRIANGLE=1 -fsyntax-only \
	  -Itests/mock_switch_sdk -Icore -Igpu \
	  gpu/deko3d_clear_main.c

host-check: host-triangle-check $(HOST_TEST) $(HOST_ABI) $(HOST_SHADERS) $(HOST_DKSH) $(HOST_DKSH_INTEGRATION) $(HOST_MOCK)
	./$(HOST_TEST)
	./$(HOST_ABI)
	./$(HOST_SHADERS)
	./$(HOST_DKSH)
	./$(HOST_DKSH_INTEGRATION)
	./$(HOST_MOCK)

host-mock-sanitized: $(HOST_MOCK_SAN) $(HOST_SHADERS_SAN) $(HOST_DKSH_SAN) $(HOST_DKSH_INTEGRATION_SAN) $(HOST_TEST_SAN) $(HOST_ABI_SAN)
	./$(HOST_MOCK_SAN)
	./$(HOST_TEST_SAN)
	./$(HOST_ABI_SAN)
	./$(HOST_SHADERS_SAN)
	./$(HOST_DKSH_SAN)
	./$(HOST_DKSH_INTEGRATION_SAN)

$(OUT).elf: $(SRC) gpu/smoke_plan.h gpu/deko3d_api_contract.h core/gpu_vertex_stream.h $(GPU_EXTRA_DEPS) | build preflight
	$(CC) $(CFLAGS) $(LDFLAGS) $(SRC) -o $@ -l$(GPU_LIB) -lstdc++ -lnx -lm

$(OUT).nacp: | build
	$(NACPTOOL) --create "$(GPU_TITLE)" "VH FoJ contributors" "$(GPU_VERSION)" $@

$(OUT).nro: $(OUT).elf $(OUT).nacp
	$(ELF2NRO) $< $@ --nacp=$(OUT).nacp

verify: $(OUT).nro
	python3 tools/validate_nro.py $(OUT).nro

clean:
	rm -f $(OUT).elf $(OUT).nacp $(OUT).nro $(HOST_TEST) $(HOST_ABI) $(HOST_MOCK) $(HOST_MOCK_SAN) $(HOST_SHADERS) $(HOST_SHADERS_SAN) $(HOST_DKSH) $(HOST_DKSH_SAN) $(HOST_DKSH_INTEGRATION) $(HOST_DKSH_INTEGRATION_SAN) $(HOST_TEST_SAN) $(HOST_ABI_SAN)
