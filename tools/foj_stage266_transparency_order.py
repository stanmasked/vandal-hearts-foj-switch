#!/usr/bin/env python3
"""Generated-only Stage266 reference for opaque-first, back-to-front blending.

This is a host-side planning/math oracle, NOT a GPU draw path or emulator proof.
Depth uses Stage263's larger-is-nearer convention (GREATER depth test).
"""
from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Sequence


COOL = (21, 202, 219)
WARM = (232, 55, 28)
VIOLET = (96, 72, 201)


@dataclass(frozen=True)
class Layer:
    name: str
    depth: float
    rgba: tuple[int, int, int, int]
    kind: str  # exactly one "opaque_rear"; others "translucent_front"


@dataclass(frozen=True)
class DrawStep:
    name: str
    depth: float
    rgba: tuple[int, int, int, int]
    blending_enabled: bool
    depth_test_enabled: bool
    depth_write_enabled: bool


def order_layers(layers: Sequence[Layer]) -> tuple[DrawStep, ...]:
    """Validate invented inputs and build the required GPU state per draw.

    Fail closed for unsupported overlapping depth or non-opaque rear. A single
    depth scalar per layer is sufficient for this experiment only; intersecting
    triangles require per-triangle or per-pixel solutions not modeled here.
    """
    if not (2 <= len(layers) <= 3):
        raise ValueError("Stage266 oracle supports one rear and 1-2 front layers")
    names = set()
    depths = set()
    rear = []
    front = []
    for layer in layers:
        if not isinstance(layer, Layer):
            raise ValueError("Only Layer inputs supported")
        if not isinstance(layer.name, str) or not layer.name or layer.name in names:
            raise ValueError("Duplicate or empty layer name")
        names.add(layer.name)
        if isinstance(layer.depth, bool) or not isinstance(layer.depth, (int, float)) or not isfinite(layer.depth) or not (0 <= layer.depth <= 1):
            raise ValueError("Depth must be finite and within [0,1]")
        if layer.depth in depths:
            raise ValueError("Ambiguous equal-depth transparent ordering")
        depths.add(layer.depth)
        if not isinstance(layer.rgba, tuple) or len(layer.rgba) != 4 or any(type(c) is not int or not 0 <= c <= 255 for c in layer.rgba):
            raise ValueError("Expected exact RGBA8 tuple")
        if layer.kind == "opaque_rear":
            if layer.rgba[3] != 255:
                raise ValueError("Rear must be opaque")
            rear.append(layer)
        elif layer.kind == "translucent_front":
            front.append(layer)
        else:
            raise ValueError("Unsupported draw pass")
    if len(rear) != 1 or len(front) != len(layers)-1:
        raise ValueError("Exactly one opaque rear layer required")
    if any(layer.depth <= rear[0].depth for layer in front):
        raise ValueError("Front layers must be nearer than rear")
    # The actual Stage265 pass submits opaque first, then translucent back-to-front.
    sorted_front = sorted(front, key=lambda layer: layer.depth)
    ordered = [rear[0], *sorted_front]
    return tuple(DrawStep(
        name=layer.name, depth=layer.depth, rgba=layer.rgba,
        blending_enabled=layer.kind == "translucent_front",
        depth_test_enabled=True,
        depth_write_enabled=layer.kind == "opaque_rear",
    ) for layer in ordered)


def composite_rgb(plan: Sequence[DrawStep]) -> tuple[int, int, int]:
    """Compute per-draw 8-bit framebuffer round-off for straight-alpha RGB."""
    if not (2 <= len(plan) <= 3):
        raise ValueError("Invalid draw count")
    if not (plan[0].depth_write_enabled and plan[0].depth_test_enabled and not plan[0].blending_enabled and plan[0].rgba[3] == 255):
        raise ValueError("First pass must write opaque background")
    pixel = tuple(plan[0].rgba[:3])
    previous_z = plan[0].depth
    for step in plan[1:]:
        if not (step.blending_enabled and step.depth_test_enabled and not step.depth_write_enabled):
            raise ValueError("Translucent pass must blend, test depth, and not write depth")
        if step.depth <= previous_z:
            raise ValueError("Translucent passes must be ordered back-to-front")
        a = step.rgba[3]
        pixel = tuple(round((a * step.rgba[i] + (255-a) * pixel[i]) / 255) for i in range(3))
        previous_z = step.depth
    return pixel


def example_three_layers() -> tuple[Layer, ...]:
    return (
        Layer("near-violet", .85, (*VIOLET, 128), "translucent_front"),
        Layer("rear-cool", .20, (*COOL, 255), "opaque_rear"),
        Layer("middle-warm", .55, (*WARM, 128), "translucent_front"),
    )


if __name__ == "__main__":
    import json
    from dataclasses import asdict
    steps = order_layers(example_three_layers())
    print(json.dumps({"scope": "host_math_only_no_guest_capture", "draws": [asdict(x) for x in steps], "expected_rgb": composite_rgb(steps)}, indent=2))
