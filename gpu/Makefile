# Optional *shader-only* deko3d bring-up.
# This does NOT build an NRO or submit GPU commands; use the independent
# switch/Makefile for existing CPU research applications.
#
# Uses official UAM ahead-of-time Maxwell shader compilation:
#   make -f gpu/Makefile
# Override UAM=/path/to/uam if not in PATH.
UAM ?= uam
GPU_OUT ?= gpu/build
VERT := gpu/shaders/foj_actor.vert
FRAG := gpu/shaders/foj_actor.frag
TRI_FRAG := gpu/shaders/foj_triangle.frag

.PHONY: all clean check-tool verify triangle triangle-verify
all: $(GPU_OUT)/foj_actor.vert.dksh $(GPU_OUT)/foj_actor.frag.dksh $(GPU_OUT)/foj_triangle.frag.dksh

check-tool:
	@command -v $(UAM) >/dev/null || { echo "ERROR: UAM shader compiler not installed; GPU shader build not verified" >&2; exit 2; }

$(GPU_OUT):
	mkdir -p $@

$(GPU_OUT)/foj_actor.vert.dksh: $(VERT) | $(GPU_OUT) check-tool
	$(UAM) -s vert -o $@ $<
	python3 -m tools.validate_dksh --expect-stage vertex $@

$(GPU_OUT)/foj_actor.frag.dksh: $(FRAG) | $(GPU_OUT) check-tool
	$(UAM) -s frag -o $@ $<
	python3 -m tools.validate_dksh --expect-stage fragment $@

# The plain UV-gradient fragment shader needs no atlas and pairs with
# the same XYZW/UV vertex shader as the original-actor research pipeline.
$(GPU_OUT)/foj_triangle.frag.dksh: $(TRI_FRAG) | $(GPU_OUT) check-tool
	$(UAM) -s frag -o $@ $<
	python3 -m tools.validate_dksh --expect-stage fragment $@

triangle: $(GPU_OUT)/foj_actor.vert.dksh $(GPU_OUT)/foj_triangle.frag.dksh

triangle-verify: triangle
	python3 -m tools.validate_dksh --expect-stage vertex $(GPU_OUT)/foj_actor.vert.dksh
	python3 -m tools.validate_dksh --expect-stage fragment $(GPU_OUT)/foj_triangle.frag.dksh

verify: all
	python3 -m tools.validate_dksh --expect-stage vertex $(GPU_OUT)/foj_actor.vert.dksh
	python3 -m tools.validate_dksh --expect-stage fragment $(GPU_OUT)/foj_actor.frag.dksh

clean:
	rm -f $(GPU_OUT)/foj_actor.vert.dksh $(GPU_OUT)/foj_actor.frag.dksh
