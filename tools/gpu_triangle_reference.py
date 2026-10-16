#!/usr/bin/env python3
"""Synthetic FoJ deko3d triangle color/coverage reference, not hardware output.

Mirrors gpu/deko3d_clear_main.c generated XYZW/UV vertices and
foj_triangle.frag's vec4(U,V,0.30,1). The deko3d flags choose a
0..1 Z range and upper-left framebuffer with +Y up in clip space.
No original PS3 game assets are read or rendered.
"""
from __future__ import annotations

import argparse
import json
from typing import Optional

WIDTH = 1280
HEIGHT = 720
# NDC x,y and shader UV. Source: gpu/deko3d_clear_main.c synthetic triangle.
VERTICES = (
    (-0.60, -0.55, 0.0, 0.0),
    (+0.60, -0.55, 1.0, 0.0),
    (0.0, +0.65, 0.5, 1.0),
)


def palette(frame: int) -> tuple[float, float, float, float]:
    if not 0 <= frame < (1 << 64):
        raise ValueError("frame must be unsigned 64-bit")
    state = (frame // 120) % 2
    intensity = 0.35 if state else 0.12
    return (0.09 + intensity, 0.12 + 0.45 * state,
            0.23 + 0.20 * state, 1.0)


def project(ndc_x: float, ndc_y: float) -> tuple[float, float]:
    """Reference mapping for chosen research viewport/orientation flags."""
    return (WIDTH * (ndc_x + 1.0) / 2.0,
            HEIGHT * (1.0 - ndc_y) / 2.0)


def triangle_uv(px: float, py: float) -> Optional[tuple[float, float]]:
    v = [(project(x, y), u, tex_v) for x, y, u, tex_v in VERTICES]
    (ax, ay), au, av = v[0]
    (bx, by), bu, bv = v[1]
    (cx, cy), cu, cv = v[2]
    det = (by - cy) * (ax - cx) + (cx - bx) * (ay - cy)
    if det == 0:
        raise ValueError("degenerate reference triangle")
    w0 = ((by - cy) * (px - cx) + (cx - bx) * (py - cy)) / det
    w1 = ((cy - ay) * (px - cx) + (ax - cx) * (py - cy)) / det
    w2 = 1.0 - w0 - w1
    if min(w0, w1, w2) < -1e-8:
        return None
    return (w0 * au + w1 * bu + w2 * cu,
            w0 * av + w1 * bv + w2 * cv)


def reference_pixel(x: int, y: int, frame: int = 0) -> dict:
    if not 0 <= x < WIDTH or not 0 <= y < HEIGHT:
        raise ValueError("pixel outside 1280x720 viewport")
    uv = triangle_uv(x + 0.5, y + 0.5)
    rgba = palette(frame) if uv is None else (uv[0], uv[1], 0.30, 1.0)
    return {
        "pixel": [x, y],
        "frame": frame,
        "inside_triangle": uv is not None,
        "uv": None if uv is None else [round(z, 6) for z in uv],
        "rgba_float": [round(z, 6) for z in rgba],
        "comparison_tolerance_per_channel": 0.02,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--frame", type=int, default=0)
    args = parser.parse_args(argv)
    probes = ((0, 0), (640, 414), (640, 200), (640, 700), (1279, 719))
    doc = {
        "status": "computed CPU reference, not GPU screenshot",
        "viewport": [WIDTH, HEIGHT],
        "triangle_ndc_uv": VERTICES,
        "frame": args.frame,
        "probes": [reference_pixel(x, y, args.frame) for x, y in probes],
        "warning": "Pixel sampling, rasterization edges, color formats and GPU state require physical Switch validation.",
    }
    print(json.dumps(doc, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
