#!/usr/bin/env python3
"""Stage 182: classify actual NeXium window captures of generated-only NROs.

This intentionally requires *screenshot pixel evidence*: a spawned process
alone, an SDK NRO compile, or a valid PNG file is not sufficient.
No real PS3 or user-owned map/material assets are needed.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image

SCHEMA = "foj-stage182-nexium-visible-synthetic-smoke-v1"
MIN_FRAME = (800, 500)
COLORS = {
    "iso_background": (13, 19, 33),
    "iso_hero": (95, 193, 244),
    "iso_enemy": (227, 82, 93),
    "iso_route": (248, 225, 108),
    "coll_background": (17, 22, 34),
    "coll_synthetic": (231, 94, 86),
    "coll_cursor": (255, 232, 140),
}


def _load_rgb(path: Path) -> Image.Image:
    with Image.open(path) as opened:
        image = opened.convert("RGB")
    if image.width < MIN_FRAME[0] or image.height < MIN_FRAME[1]:
        raise ValueError("Emulator screenshot smaller than expected")
    if image.width > 4096 or image.height > 2160:
        raise ValueError("Unexpectedly large emulator screenshot")
    return image


def count_near(image: Image.Image, rgb: tuple[int, int, int],
               tolerance: int = 14) -> int:
    # Exact palette evidence; tolerance permits minor desktop conversion
    # without treating unrelated dark windows as successful guest output.
    return sum(
        1 for pixel in image.getdata()
        if all(abs(pixel[i]-rgb[i]) <= tolerance for i in range(3))
    )


def verify_emulator_captures(iso: Path, iso_route: Path, coll: Path) -> dict:
    before = _load_rgb(iso)
    after = _load_rgb(iso_route)
    view = _load_rgb(coll)

    if before.size != after.size:
        raise ValueError("Two screenshots of isometric NRO differ in size")

    before_bg = count_near(before, COLORS["iso_background"])
    before_hero = count_near(before, COLORS["iso_hero"])
    before_enemy = count_near(before, COLORS["iso_enemy"])
    route_before = count_near(before, COLORS["iso_route"])
    route_after = count_near(after, COLORS["iso_route"])
    after_hero = count_near(after, COLORS["iso_hero"])
    coll_bg = count_near(view, COLORS["coll_background"])
    coll_synth = count_near(view, COLORS["coll_synthetic"])
    coll_cursor = count_near(view, COLORS["coll_cursor"])

    # A blank/desktop/loader capture must not pass solely from window
    # existence. The colors below come from independently-authored
    # synthetic CPU framebuffer renderer and synthetic-data status marker.
    if before_bg < 2500 or before_hero < 100 or before_enemy < 100:
        raise ValueError("Isometric guest scene was not visibly rendered")
    if after_hero < 100:
        raise ValueError("Hero was missing after emulator input sequence")
    if route_after < 30 or route_after < route_before + 25:
        raise ValueError("Keyboard selection/move did not show route pixels")
    if coll_bg < 2500 or coll_synth < 150 or coll_cursor < 20:
        raise ValueError("Generated-only COLL guest scene was not visible")

    return {
        "schema": SCHEMA,
        "research_scope": "two_asset_free_homebrew_nro_guest_sessions",
        "emulator": "NeXium",
        "isometric_initial_visible": True,
        "isometric_route_after_emulated_input_visible": True,
        "coll_generated_fallback_visible": True,
        "isometric_initial_dimensions": list(before.size),
        "coll_dimensions": list(view.size),
        "isometric_initial_hero_pixel_count": before_hero,
        "isometric_initial_enemy_pixel_count": before_enemy,
        "isometric_route_pixels_before_input": route_before,
        "isometric_route_pixels_after_input": route_after,
        "coll_synthetic_status_pixel_count": coll_synth,
        "coll_cursor_pixel_count": coll_cursor,
        "physical_switch_execution_verified": False,
        "original_foj_gameplay_verified": False,
        "original_ps3_assets_used": False,
        "gpu_scanout_on_physical_switch_verified": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--iso", type=Path, required=True)
    parser.add_argument("--iso-route", type=Path, required=True)
    parser.add_argument("--coll", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = verify_emulator_captures(
            args.iso, args.iso_route, args.coll)
        # No user image data/absolute paths published in JSON receipt.
        with args.report.open("x", encoding="utf-8") as handle:
            json.dump(result, handle, sort_keys=True, indent=2)
            handle.write("\n")
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    print("Two NeXium NRO screens observed; synthetic route and COLL "
          "colors match. No physical Switch verification.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
