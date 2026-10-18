#!/usr/bin/env python3
"""Stage 184: check cursor, ZR zoom and six raw channels in real NeXium frames.

Use images rendered with the exact C NRO heatmap implementation as a
pixel-position reference. A persistent synthetic status rectangle anchors
the framebuffer inside potentially decorated emulator windows.
No original PS3 resources or physical Nintendo Switch evidence.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image, ImageChops

SCHEMA = "foj-stage184-nexium-coll-cursor-zoom-six-channels-v1"
STATES = (
    "cursor-right", "zoom", "ch1", "ch2", "ch3", "ch4", "ch5", "ch0",
)
SYNTHETIC_STATUS = (231, 94, 86)
BACKGROUND = (17, 22, 34)


def load(path: Path) -> Image.Image:
    with Image.open(path) as image:
        frame = image.convert("RGB")
    if not 800 <= frame.width <= 4096 or not 500 <= frame.height <= 2160:
        raise ValueError("Invalid guest or reference screenshot dimensions")
    return frame


def anchor(frame: Image.Image) -> tuple[int, int]:
    """Locate only the top-right synthetic status rectangle, not map pixels."""
    xs = []
    ys = []
    pix = frame.load()
    for y in range(min(frame.height, 105)):
        for x in range(max(0, frame.width - 270), frame.width):
            r, g, b = pix[x, y]
            if max(abs(r - 231), abs(g - 94), abs(b - 86)) <= 3:
                xs.append(x)
                ys.append(y)
    if len(xs) < 250 or max(xs) - min(xs) < 20 or max(ys) - min(ys) < 14:
        raise ValueError("Actual guest frame lacks the synthetic COLL status marker")
    return min(xs) - 1235, min(ys) - 16


def source_pixel_agreement(frame: Image.Image, ref: Image.Image) -> tuple[float, int]:
    if ref.size != (1280, 720):
        raise ValueError("Incorrect portable C reference resolution")
    shift_x, shift_y = anchor(frame)
    guest = frame.load()
    expected = ref.load()
    checked = 0
    agreed = 0
    # Spread tests across the visible drawn 50x50 map. Exclude dark
    # background, HUD, and marker-only regions: they are too easy to
    # match without rendering the correct grid/channel.
    for y in range(85, 660, 7):
        for x in range(120, 1170, 7):
            rgb = expected[x, y]
            if rgb == BACKGROUND:
                continue
            gx, gy = x + shift_x, y + shift_y
            if gx < 0 or gy < 0 or gx >= frame.width or gy >= frame.height:
                continue
            checked += 1
            observed = guest[gx, gy]
            if max(abs(rgb[i] - observed[i]) for i in range(3)) <= 3:
                agreed += 1
    if checked < 900:
        raise ValueError("C reference did not contain enough visible map pixels")
    return agreed / checked, checked


def difference(a: Image.Image, b: Image.Image) -> int:
    if a.size != b.size:
        raise ValueError("NeXium changed window dimensions between button presses")
    delta = ImageChops.difference(a, b)
    return sum(1 for rgb in delta.getdata() if max(rgb) > 12)


def verify_input_sequence(
    restored_path: Path, captured: dict[str, Path], refs: dict[str, Path]
) -> dict:
    if set(captured) != set(STATES) or set(refs) != set(STATES):
        raise ValueError("All eight ordered COLL input states are required")
    before = load(restored_path)
    anchor(before)
    first = before
    agreements = {}
    deltas = {}
    for state in STATES:
        guest = load(captured[state])
        reference = load(refs[state])
        score, count = source_pixel_agreement(guest, reference)
        if score < 0.87:
            raise ValueError(f"NeXium COLL input state did not match C renderer: {state}")
        delta = difference(first, guest)
        # A single cursor step moves only its gold outline; zoom or
        # changing a raw channel must change substantially more.
        threshold = 70 if state == "cursor-right" else 3000
        if state != "ch0" and delta < threshold:
            raise ValueError(f"No visible guest input reaction: {state}")
        if state == "ch0" and delta < 3000:
            raise ValueError("Sixth R press failed to change from raw channel 5")
        agreements[state] = round(score, 5)
        deltas[state] = delta
        first = guest

    # After six R presses channel 0 must be restored with cursor at
    # (26,25) and tile size 14; the source image is the same as 'zoom'.
    return_delta = difference(load(captured["zoom"]), load(captured["ch0"]))
    if return_delta > max(4000, before.width * before.height // 100):
        raise ValueError("Six-channel wrap did not restore the zoomed raw channel 0")

    return {
        "schema": SCHEMA,
        "emulator": "NeXium",
        "scope": "generated_only_coll_diagnostic_homebrew",
        "input_sequence": ["DRight", "ZR"] + ["R"] * 6,
        "keyboard_mapping": {"DRight": "Right", "ZR": "t", "R": "e"},
        "states_verified": list(STATES),
        "host_c_reference_matches": agreements,
        "guest_changed_pixel_counts": deltas,
        "pixels_changed_after_six_channel_wrap": return_delta,
        "observed_cursor_move": True,
        "observed_zoom_change": True,
        "observed_six_raw_channel_cycle": True,
        "original_ps3_assets_used": False,
        "physical_switch_execution_verified": False,
        "physical_gpu_scanout_verified": False,
        "original_gameplay_verified": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    try:
        captured = {state: args.evidence / f"coll-{state}.png"
                    for state in STATES}
        refs = {state: args.evidence / f"ref-coll-{state}.png"
                for state in STATES}
        result = verify_input_sequence(
            args.evidence / "coll-heat-return-after-y.png", captured, refs
        )
        with args.report.open("x", encoding="utf-8") as output:
            json.dump(result, output, indent=2, sort_keys=True)
            output.write("\n")
    except (OSError, ValueError) as error:
        parser.error(str(error))
    print("NeXium COLL cursor, ZR zoom, all six R channels and wrap passed; "
          "no physical Switch run verified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
