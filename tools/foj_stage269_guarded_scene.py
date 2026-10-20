"""Stage269 generated-only fail-closed preflight before NeXium SD writes.

This validates the exact FOJRM001 geometry that Stage267 would install, not
hard-coded semantic layer labels. It does NOT protect arbitrary native NRO
input or prove correct perspective transparency.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import struct

from tools.foj_stage267_generated_multiblend_sd import (
    CASES, generated_three_layer_mesh, install_three_layer,
)
from tools.foj_stage268_transparency_crossing import (
    Triangle, UnsafeTransparencyOrder, plan_back_to_front,
)

_NAMES = ("violet", "warm", "cool")
_EXPECTED = ("cool", "warm", "violet")
_VERTEX_OFFSET = 28 + 32 + 3 * 8
_STRIDE = 76


def guard_three_layer_mesh(mesh: bytes) -> tuple[str, ...]:
    """Reject malformed or crossing generated 3-section meshes before use."""
    if len(mesh) != _VERTEX_OFFSET + 9 * _STRIDE or mesh[:8] != b"FOJRM001":
        raise ValueError("Not the complete 3-triangle generated actor")
    if struct.unpack_from("<IIIII", mesh, 8) != (1, 1, 9, 3, 0):
        raise ValueError("Unexpected actor header")
    if struct.unpack_from("<IIIIII", mesh, 60) != (0, 3, 3, 3, 6, 3):
        raise ValueError("Unexpected actor sections")
    raw = []
    for slot, name in enumerate(_NAMES):
        verts = []
        for vertex in range(3):
            xyz = struct.unpack_from("<fff", mesh,
                         _VERTEX_OFFSET + (slot * 3 + vertex) * _STRIDE)
            # Stage267 uses private_camera with yaw=pitch=0 and one shared
            # affine Z normalization, preserving all strict depth signs.
            x, y, z = xyz
            verts.append((x, y, z))
        raw.append((name, tuple(verts)))
    # Fit all three triangles to the same strictly monotonic depth range.
    flat_z = [vertex[2] for _, vertices in raw for vertex in vertices]
    # Checking finiteness BEFORE min/max prevents NaN from evading ordering.
    from math import isfinite
    if not all(isfinite(v) for v in flat_z):
        raise ValueError("Nonfinite camera depth")
    low, high = min(flat_z), max(flat_z)
    if high - low <= 1e-6:
        raise UnsafeTransparencyOrder("Degenerate scene depth span")
    tris = tuple(Triangle(name, tuple(
        (x, y, .01 + .98 * (z - low) / (high-low)) for x,y,z in vertices))
        for name, vertices in raw)
    order = plan_back_to_front(tris)
    if order != _EXPECTED:
        raise UnsafeTransparencyOrder("Generated fixed NRO draw order disagrees "
                                      f"with depth constraints: {order}")
    return order


def install_guarded(root: Path, shaders: Path, case: str) -> dict:
    if case not in CASES:
        raise ValueError("Unknown synthetic alpha case")
    root = Path(root)
    if root.exists() or root.is_symlink():
        raise ValueError("Refusing existing generated SD root")
    # No filesystem changes or DKSH reading before geometry is accepted.
    order = guard_three_layer_mesh(generated_three_layer_mesh())
    report = install_three_layer(root, shaders, case)
    report.update({
        "stage269_geometry_guard": "safe_fixed_back_to_front",
        "stage269_checked_order": list(order),
        "stage269_native_runtime_guard": False,
        "stage269_actual_neixum_capture_verified": False,
    })
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--shaders", type=Path, required=True)
    parser.add_argument("--scenario", choices=tuple(CASES), required=True)
    args = parser.parse_args(argv)
    receipt = install_guarded(args.data_root,args.shaders,args.scenario)
    print(json.dumps(receipt,sort_keys=True))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
